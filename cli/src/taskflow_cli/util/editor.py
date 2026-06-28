"""Compose a message body from -m, stdin, or $EDITOR.

Pattern mirrors `git commit`: try -m first, then --stdin, then editor.
Lines starting with '#' in editor output are stripped (template comments).
Empty body after stripping aborts with exit 2.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

import typer


# Sentinel — distinguishes "user did not pass -m" from "user passed -m ''"
_UNSET = object()


def compose_body(
    *,
    message: str | None = None,
    message_stdin: bool = False,
    editor_template: str = "",
) -> str:
    """Return the composed body. Raises typer.Exit(2) on user error."""
    err = sys.stderr

    # Mutual exclusion
    if message is not None and message_stdin:
        print(
            "error: --message and --message-stdin are mutually exclusive",
            file=err,
        )
        raise typer.Exit(code=2)

    if message is not None:
        body = message.strip()
        if not body:
            print("error: empty message", file=err)
            raise typer.Exit(code=2)
        return body

    if message_stdin:
        body = sys.stdin.read().strip()
        if not body:
            print("error: empty message from stdin", file=err)
            raise typer.Exit(code=2)
        return body

    return _editor_body(editor_template)


def _editor_body(template: str) -> str:
    """Open $EDITOR with a template; strip '#' lines; return cleaned body."""
    editor = (
        os.environ.get("EDITOR")
        or shutil.which("nano")
        or shutil.which("vi")
    )
    if not editor:
        print(
            "error: no editor found; set $EDITOR or use -m / --message-stdin",
            file=sys.stderr,
        )
        raise typer.Exit(code=2)

    initial = (
        ""
        if not template
        else "\n".join(f"# {line}" for line in template.splitlines()) + "\n\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".tflowctl.md", delete=False, encoding="utf-8"
    ) as f:
        path = f.name
        f.write(initial)
        f.flush()

    try:
        # shlex split to support EDITOR='code --wait' etc.
        import shlex
        cmd = shlex.split(editor) + [path]
        subprocess.run(cmd, check=True)

        with open(path, encoding="utf-8") as f:
            raw = f.read()
    finally:
        os.unlink(path)

    # Strip comment lines and surrounding whitespace
    body = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    ).strip()

    if not body:
        print("error: aborting due to empty message", file=sys.stderr)
        raise typer.Exit(code=2)

    return body
