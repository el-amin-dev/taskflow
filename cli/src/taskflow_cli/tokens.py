"""Token persistence: atomic, 0600, single-flight refresh lock.

File-backed implementation. A future keychain/libsecret backend
would replace this module under the same call signatures.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Tokens:
    """Persistent credentials. expires_at is epoch seconds (UTC)."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_at: int

    @classmethod
    def from_response(cls, body: dict, now: int | None = None) -> "Tokens":
        """Build from /login or /refresh response. expires_in -> expires_at."""
        clock = now if now is not None else int(time.time())
        return cls(
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            token_type=body.get("token_type", "bearer"),
            expires_at=clock + int(body["expires_in"]),
        )

    def is_access_expired(self, skew_seconds: int = 30, now: int | None = None) -> bool:
        """True if the access token has expired (with skew for clock drift)."""
        clock = now if now is not None else int(time.time())
        return clock >= self.expires_at - skew_seconds


def load(credentials_path: Path) -> Tokens | None:
    """Read credentials. Returns None when no file (= not logged in)."""
    if not credentials_path.exists():
        return None
    data = json.loads(credentials_path.read_text(encoding="utf-8"))
    return Tokens(**data)


def save(credentials_path: Path, tokens: Tokens) -> None:
    """Atomic write, mode 0600. Creates parent dir (0700) if missing."""
    credentials_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".credentials.", dir=credentials_path.parent)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(tokens), f)
        os.replace(tmp, credentials_path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def delete(credentials_path: Path) -> None:
    """Idempotent: succeed silently if nothing's there."""
    with contextlib.suppress(FileNotFoundError):
        credentials_path.unlink()


@contextlib.contextmanager
def refresh_lock(credentials_path: Path) -> Iterator[None]:
    """Exclusive lock around the refresh critical section.

    POSIX only (Linux/macOS). Held from 'read refresh token' through
    'POST /v1/auth/refresh' through 'write new tokens', so two concurrent
    CLI invocations can't both spend the same single-use refresh token
    (which would trigger family-kill on the server side).
    """
    lock_path = credentials_path.parent / (credentials_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
