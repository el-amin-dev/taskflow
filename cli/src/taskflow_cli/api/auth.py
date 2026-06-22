"""Auth API endpoints: thin wrappers over Transport.

Each function takes a Transport (which carries the bearer header if any)
and returns the parsed response. Session/refresh orchestration lives
in session.py, not here.
"""
from __future__ import annotations

from typing import Any

from taskflow_cli.transport import Transport


def register(client: Transport, *, email: str, password: str) -> dict[str, Any]:
    """POST /v1/auth/register -> UserResponse."""
    return client.post(
        "/v1/auth/register", json={"email": email, "password": password}
    )


def login(client: Transport, *, email: str, password: str) -> dict[str, Any]:
    """POST /v1/auth/login -> TokenResponse."""
    return client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )


def refresh(client: Transport, *, refresh_token: str) -> dict[str, Any]:
    """POST /v1/auth/refresh -> TokenResponse (rotates the refresh token)."""
    return client.post(
        "/v1/auth/refresh", json={"refresh_token": refresh_token}
    )


def logout(client: Transport, *, refresh_token: str) -> None:
    """POST /v1/auth/logout -> 204 (idempotent)."""
    client.post("/v1/auth/logout", json={"refresh_token": refresh_token})


def me(client: Transport) -> dict[str, Any]:
    """GET /v1/auth/me -> UserResponse. Requires Bearer."""
    return client.get("/v1/auth/me")
