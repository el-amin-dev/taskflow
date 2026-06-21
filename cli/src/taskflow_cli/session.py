"""Session orchestrator: load tokens, refresh inside the lock, retry on 401.

Composes transport.py (wire) with tokens.py (persistence) and
api/auth.py (refresh endpoint). Owns the read-call-refresh-retry-write
sequence that prevents the single-use-refresh race.

Same call shape as Transport (.get/.post/.patch/.delete), so api/*
modules accept either anonymous transports or authenticated sessions
transparently.
"""
from __future__ import annotations

from typing import Any

from taskflow_cli import tokens
from taskflow_cli.api import auth as api_auth
from taskflow_cli.config import Config
from taskflow_cli.errors import EXIT_AUTH, ApiError, InvalidToken
from taskflow_cli.transport import Transport


class SessionExpired(ApiError):
    """The refresh token is dead — caller must re-authenticate."""

    exit_code = EXIT_AUTH
    code = None


class Session:
    """Per-invocation orchestrator. Loads tokens at construction."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._tokens: tokens.Tokens | None = tokens.load(cfg.credentials_path)

    # ---------- state ----------

    @property
    def is_authenticated(self) -> bool:
        return self._tokens is not None

    @property
    def access_token(self) -> str | None:
        return self._tokens.access_token if self._tokens else None

    def save_tokens(self, body: dict[str, Any]) -> None:
        """Persist a TokenResponse (from /login or /refresh). Atomic 0600."""
        self._tokens = tokens.Tokens.from_response(body)
        tokens.save(self._cfg.credentials_path, self._tokens)

    def clear(self) -> None:
        """Wipe credentials. Idempotent."""
        self._tokens = None
        tokens.delete(self._cfg.credentials_path)

    # ---------- transports ----------

    def anonymous_client(self) -> Transport:
        """No auth header — for /register, /login, /refresh, /logout."""
        return Transport(self._cfg.api_url)

    # ---------- authenticated calls (same shape as Transport) ----------

    def get(self, path: str, *, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, *, json: Any = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, *, json: Any = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # ---------- internals ----------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
    ) -> Any:
        if not self._tokens:
            raise SessionExpired("not authenticated; run `tflowctl auth login`")

        # Proactive: refresh if access is at/near expiry
        if self._tokens.is_access_expired():
            self._refresh()

        try:
            return self._call(method, path, json=json, params=params)
        except InvalidToken:
            # Reactive: server rejected even though we thought it was good
            self._refresh()
            return self._call(method, path, json=json, params=params)

    def _call(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
    ) -> Any:
        assert self._tokens is not None
        with Transport(self._cfg.api_url, access_token=self._tokens.access_token) as t:
            if method == "GET":
                return t.get(path, params=params)
            if method == "POST":
                return t.post(path, json=json)
            if method == "PATCH":
                return t.patch(path, json=json)
            if method == "DELETE":
                return t.delete(path)
            raise ValueError(f"unsupported method: {method}")

    def _refresh(self) -> None:
        """Refresh tokens inside the lock. Wipes + raises on failure."""
        assert self._tokens is not None

        with tokens.refresh_lock(self._cfg.credentials_path):
            # Another process may have refreshed while we waited on the lock
            fresh = tokens.load(self._cfg.credentials_path)
            if fresh and fresh.refresh_token != self._tokens.refresh_token:
                self._tokens = fresh
                return

            # We do the refresh ourselves
            with self.anonymous_client() as t:
                try:
                    body = api_auth.refresh(
                        t, refresh_token=self._tokens.refresh_token
                    )
                except InvalidToken as e:
                    self.clear()
                    raise SessionExpired(
                        "session expired; run `tflowctl auth login`"
                    ) from e

            self._tokens = tokens.Tokens.from_response(body)
            tokens.save(self._cfg.credentials_path, self._tokens)
