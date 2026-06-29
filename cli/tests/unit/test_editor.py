"""Tests for util/editor.py: body composition via -m, stdin, or EDITOR.

Mocking strategy:
- monkeypatch.setenv / delenv for $EDITOR
- monkeypatch.setattr(editor.shutil, 'which', ...) for the editor fallback chain
- monkeypatch.setattr(editor.subprocess, 'run', ...) for editor invocation
- monkeypatch.setattr(sys, 'stdin', io.StringIO(...)) for the stdin path
"""
from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest
import typer

from taskflow_cli.util import editor


# --- mutex check ----------------------------------------------------------

def test_message_and_stdin_together_is_usage_error():
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body(message="m", message_stdin=True)
    assert exc.value.exit_code == 2


class _RaisingStdin:
    """Replaces sys.stdin during a test that must NOT touch it."""

    def read(self, *a, **kw):
        raise AssertionError("stdin was read when it must not be")


def test_mutex_check_fires_before_stdin_is_read(monkeypatch):
    """Locked design contract: scripts must never hang on stdin in the mutex case."""
    monkeypatch.setattr(sys, "stdin", _RaisingStdin())
    with pytest.raises(typer.Exit):
        editor.compose_body(message="m", message_stdin=True)


# --- -m path --------------------------------------------------------------

def test_message_path_strips_surrounding_whitespace():
    assert editor.compose_body(message="  hello  ") == "hello"


def test_empty_message_is_usage_error():
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body(message="   ")
    assert exc.value.exit_code == 2


# --- stdin path -----------------------------------------------------------

def test_stdin_path_returns_stripped_body(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("  body from pipe  \n"))
    assert editor.compose_body(message_stdin=True) == "body from pipe"


def test_empty_stdin_is_usage_error(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body(message_stdin=True)
    assert exc.value.exit_code == 2


def test_whitespace_only_stdin_is_usage_error(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("   \n   \n"))
    with pytest.raises(typer.Exit):
        editor.compose_body(message_stdin=True)


# --- editor path: helpers -------------------------------------------------

def _fake_run_writing(content: str):
    """Return a subprocess.run replacement that writes `content` to the temp file.

    The source builds `cmd = shlex.split(editor) + [path]`, so the temp file
    path is always the LAST element. We use that to write to it.
    """
    def fake_run(cmd, check=True):
        path = cmd[-1]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return MagicMock(returncode=0)
    return fake_run


# --- editor path: behavior ------------------------------------------------

def test_editor_path_returns_body(monkeypatch):
    monkeypatch.setenv("EDITOR", "fake-editor")
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing("hello from editor\n"))
    assert editor.compose_body() == "hello from editor"


def test_editor_strips_comment_lines(monkeypatch):
    monkeypatch.setenv("EDITOR", "fake-editor")
    raw = (
        "# This is a comment\n"
        "real content\n"
        "  # indented comment\n"
        "more content\n"
    )
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing(raw))
    assert editor.compose_body() == "real content\nmore content"


def test_editor_only_comments_aborts(monkeypatch):
    """A session with only comment lines is treated as an empty message — abort."""
    monkeypatch.setenv("EDITOR", "fake-editor")
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing("# only comments\n# more\n"))
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body()
    assert exc.value.exit_code == 2


def test_editor_truly_empty_file_aborts(monkeypatch):
    monkeypatch.setenv("EDITOR", "fake-editor")
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing(""))
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body()
    assert exc.value.exit_code == 2


# --- editor path: fallback chain ------------------------------------------

def test_editor_falls_back_to_nano_when_env_unset(monkeypatch):
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(
        editor.shutil, "which",
        lambda name: "/usr/bin/nano" if name == "nano" else None,
    )
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing("body"))
    assert editor.compose_body() == "body"


def test_editor_falls_back_to_vi_when_nano_missing(monkeypatch):
    monkeypatch.delenv("EDITOR", raising=False)
    table = {"nano": None, "vi": "/usr/bin/vi"}
    monkeypatch.setattr(editor.shutil, "which", lambda n: table.get(n))
    monkeypatch.setattr(editor.subprocess, "run", _fake_run_writing("body"))
    assert editor.compose_body() == "body"


def test_no_editor_anywhere_is_usage_error(monkeypatch):
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(editor.shutil, "which", lambda n: None)
    with pytest.raises(typer.Exit) as exc:
        editor.compose_body()
    assert exc.value.exit_code == 2


# --- editor path: invocation details --------------------------------------

def test_editor_with_args_is_shlex_split(monkeypatch):
    """EDITOR='code --wait' splits into ['code', '--wait', <path>]."""
    monkeypatch.setenv("EDITOR", "fake-editor --wait")

    seen = {}
    def fake_run(cmd, check=True):
        seen["cmd"] = list(cmd)
        with open(cmd[-1], "w", encoding="utf-8") as f:
            f.write("ok")
        return MagicMock()

    monkeypatch.setattr(editor.subprocess, "run", fake_run)
    editor.compose_body()

    assert seen["cmd"][0] == "fake-editor"
    assert seen["cmd"][1] == "--wait"
    assert seen["cmd"][2].endswith(".tflowctl.md")


def test_editor_template_appears_as_comment_lines(monkeypatch):
    """The editor_template arg is pre-written into the tempfile as # lines."""
    monkeypatch.setenv("EDITOR", "fake-editor")

    captured = {}
    def fake_run(cmd, check=True):
        path = cmd[-1]
        with open(path, encoding="utf-8") as f:
            captured["initial"] = f.read()
        # Write something non-empty so compose_body doesn't abort
        with open(path, "w", encoding="utf-8") as f:
            f.write("user content")
        return MagicMock()

    monkeypatch.setattr(editor.subprocess, "run", fake_run)
    editor.compose_body(editor_template="Line A\nLine B")

    assert "# Line A" in captured["initial"]
    assert "# Line B" in captured["initial"]
