"""Tests for tokens.py: persistence, expiry math, and refresh-lock semantics.

What's tested:
- Tokens dataclass shape and from_response math
- is_access_expired with skew
- save/load round-trip and atomicity-adjacent invariants (mode, parent dir)
- save error path cleans up the tmpfile
- delete is idempotent
- refresh_lock acquires, lock file persists, double-acquire blocks
"""
from __future__ import annotations

import fcntl
import json
import os
import stat
from pathlib import Path

import pytest

from taskflow_cli import tokens
from taskflow_cli.tokens import Tokens

# --- Tokens.from_response ---------------------------------------------------

def test_from_response_computes_absolute_expiry():
    """from_response maps `expires_in` (relative) to `expires_at` (absolute)."""
    body = {
        "access_token": "a",
        "refresh_token": "r",
        "token_type": "bearer",
        "expires_in": 900,
    }
    t = Tokens.from_response(body, now=1_000_000)
    assert t.access_token == "a"
    assert t.refresh_token == "r"
    assert t.token_type == "bearer"
    assert t.expires_at == 1_000_900


def test_from_response_defaults_token_type():
    """Backends that omit token_type get 'bearer' as a sane default."""
    body = {"access_token": "a", "refresh_token": "r", "expires_in": 60}
    t = Tokens.from_response(body, now=0)
    assert t.token_type == "bearer"


def test_from_response_raises_on_missing_required_field():
    """Missing access_token, refresh_token, or expires_in is a programming error."""
    with pytest.raises(KeyError):
        Tokens.from_response({"refresh_token": "r", "expires_in": 60}, now=0)


# --- Tokens.is_access_expired ----------------------------------------------

def _tok(expires_at: int) -> Tokens:
    return Tokens(access_token="a", refresh_token="r", token_type="bearer", expires_at=expires_at)


def test_is_access_expired_after_absolute_expiry():
    assert _tok(expires_at=1000).is_access_expired(skew_seconds=0, now=1001) is True


def test_is_access_expired_before_absolute_expiry_no_skew():
    assert _tok(expires_at=1000).is_access_expired(skew_seconds=0, now=999) is False


def test_is_access_expired_skew_makes_it_expire_early():
    """skew_seconds=30 means we treat it as expired 30s before the real cutoff."""
    # 970 is 30s before expires_at=1000 → exactly at the skew boundary
    assert _tok(expires_at=1000).is_access_expired(skew_seconds=30, now=970) is True
    # 969 is 31s before → still fresh
    assert _tok(expires_at=1000).is_access_expired(skew_seconds=30, now=969) is False


def test_is_access_expired_exact_boundary_is_expired():
    """At exactly expires_at, the token is considered expired (>= comparison)."""
    assert _tok(expires_at=1000).is_access_expired(skew_seconds=0, now=1000) is True


# --- save / load round-trip ------------------------------------------------

def test_save_creates_file_with_mode_0600(tmp_path: Path):
    creds = tmp_path / "credentials"
    t = _tok(expires_at=999)
    tokens.save(creds, t)
    assert creds.exists()
    mode = stat.S_IMODE(os.stat(creds).st_mode)
    assert mode == 0o600


def test_save_creates_parent_directory_with_mode_0700(tmp_path: Path):
    """Parent dir gets 0700 — owner-only access to the directory holding secrets."""
    creds = tmp_path / "nested" / "deep" / "credentials"
    tokens.save(creds, _tok(expires_at=1))
    parent_mode = stat.S_IMODE(os.stat(creds.parent).st_mode)
    # We assert subset because the umask may add bits we don't control,
    # but the meaningful invariant is "no group/other read or write".
    assert parent_mode & 0o077 == 0


def test_save_writes_json_with_all_fields(tmp_path: Path):
    creds = tmp_path / "credentials"
    t = Tokens(access_token="acc", refresh_token="ref", token_type="bearer", expires_at=42)
    tokens.save(creds, t)
    data = json.loads(creds.read_text())
    assert data == {
        "access_token": "acc",
        "refresh_token": "ref",
        "token_type": "bearer",
        "expires_at": 42,
    }


def test_save_then_load_round_trip(tmp_path: Path):
    creds = tmp_path / "credentials"
    t = Tokens(access_token="acc", refresh_token="ref", token_type="bearer", expires_at=42)
    tokens.save(creds, t)
    loaded = tokens.load(creds)
    assert loaded == t  # dataclass equality


def test_save_is_atomic_by_replacing_existing_file(tmp_path: Path):
    """A second save replaces the first; no tempfile residue left behind."""
    creds = tmp_path / "credentials"
    tokens.save(creds, _tok(expires_at=1))
    tokens.save(creds, _tok(expires_at=2))
    leftovers = [p for p in creds.parent.iterdir() if p.name.startswith(".credentials.")]
    assert leftovers == []
    assert json.loads(creds.read_text())["expires_at"] == 2


def test_save_cleans_up_tmpfile_on_serialization_failure(tmp_path: Path, monkeypatch):
    """If json.dump explodes mid-write, the tempfile must be unlinked."""
    creds = tmp_path / "credentials"

    def boom(*args, **kwargs):
        raise RuntimeError("simulated dump failure")

    monkeypatch.setattr(tokens.json, "dump", boom)
    with pytest.raises(RuntimeError, match="simulated"):
        tokens.save(creds, _tok(expires_at=1))

    # No final file (atomic replace never ran)
    assert not creds.exists()
    # And no leftover tmp file
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".credentials.")]
    assert leftovers == []


# --- load --------------------------------------------------------------------

def test_load_returns_none_when_file_missing(tmp_path: Path):
    """No file = not logged in. Callers branch on None."""
    assert tokens.load(tmp_path / "nonexistent") is None


# --- delete ------------------------------------------------------------------

def test_delete_is_idempotent(tmp_path: Path):
    """Calling delete on a non-existent file must not raise."""
    creds = tmp_path / "credentials"
    tokens.delete(creds)  # not there yet
    tokens.save(creds, _tok(expires_at=1))
    tokens.delete(creds)
    tokens.delete(creds)  # gone, but still safe
    assert not creds.exists()


# --- refresh_lock ------------------------------------------------------------

def test_refresh_lock_creates_lock_file_next_to_credentials(tmp_path: Path):
    """Lock file sits at <credentials>.lock — visible during the critical section."""
    creds = tmp_path / "credentials"
    with tokens.refresh_lock(creds):
        lock_path = creds.parent / "credentials.lock"
        assert lock_path.exists()


def test_refresh_lock_is_exclusive_within_process(tmp_path: Path):
    """A second attempt to take the lock non-blockingly must fail while it's held."""
    creds = tmp_path / "credentials"
    lock_path = creds.parent / "credentials.lock"
    creds.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    with tokens.refresh_lock(creds):
        # Try a non-blocking acquire on the SAME lock file from a separate fd.
        # On Linux, flock is per-open-file-description, so this is a fair test.
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    # After exit, a non-blocking acquire must succeed
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
