"""HTTP transport: httpx wrapper that unwraps the API error envelope.

Sync (a CLI invocation has no concurrency to exploit). Returns parsed
JSON on 2xx; raises a typed ApiError subclass otherwise. The session
layer composes this with tokens.py for the refresh dance.
"""
from __future__ import annotations

from typing import Any

import httpx

from taskflow_cli.errors import (
    CODE_TO_EXCEPTION,
    ApiError,
    NetworkError,
    ServerError,
    ValidationError,
)

DEFAULT_TIMEOUT = 30.0


class Transport:
    """Thin httpx wrapper. Use as a context manager."""

    def __init__(
        self,
        base_url: str,
        *,
        access_token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=timeout)

    def __enter__(self) -> "Transport":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

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
        try:
            resp = self._client.request(method, path, json=json, params=params)
        except httpx.RequestError as e:
            raise NetworkError(f"{type(e).__name__}: {e}") from e
        return self._parse(resp)

    @staticmethod
    def _parse(resp: httpx.Response) -> Any:
        status = resp.status_code

        if 200 <= status < 300:
            if status == 204 or not resp.content:
                return None
            return resp.json()

        if status >= 500:
            raise ServerError(f"server error ({status})", http_status=status)

        # 4xx — best-effort JSON parse, fall back to raw text
        try:
            body = resp.json()
        except ValueError:
            raise ApiError(resp.text or f"http {status}", http_status=status)

        if status == 422:
            # FastAPI shape: {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
            detail = body.get("detail", []) if isinstance(body, dict) else []
            if isinstance(detail, list) and detail and isinstance(detail[0], dict):
                first = detail[0]
                msg = first.get("msg", "validation failed")
                loc = ".".join(str(x) for x in first.get("loc", []))
                message = f"{loc}: {msg}" if loc else msg
            else:
                message = "validation failed"
            raise ValidationError(message, http_status=422)

        # other 4xx — our envelope: {"detail": {"detail": "...", "code": "..."}}
        envelope = body.get("detail", {}) if isinstance(body, dict) else {}
        if isinstance(envelope, dict):
            message = envelope.get("detail") or f"http {status}"
            code = envelope.get("code")
        else:
            message = str(envelope) or f"http {status}"
            code = None

        exc_cls = CODE_TO_EXCEPTION.get(code, ApiError) if code else ApiError
        raise exc_cls(message, http_status=status)
