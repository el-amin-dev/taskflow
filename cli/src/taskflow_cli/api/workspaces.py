"""Workspaces API endpoints: thin wrappers over Client."""
from __future__ import annotations

from typing import Any

from taskflow_cli.transport import Client


def list_all(client: Client) -> list[dict[str, Any]]:
    """GET /v1/workspaces -> WorkspaceResponse[] (caller's memberships only)."""
    return client.get("/v1/workspaces")


def create(client: Client, *, name: str) -> dict[str, Any]:
    """POST /v1/workspaces -> WorkspaceResponse."""
    return client.post("/v1/workspaces", json={"name": name})
