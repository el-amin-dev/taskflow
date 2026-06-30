"""Comment API client. Functions wrap one HTTP call each.

Backend: POST/GET on .../comments, PATCH/DELETE on .../comments/{id}.
Pagination: GET supports cursor + limit. list_all walks all pages.
RBAC: only the author can PATCH/DELETE; non-author returns 403 not_comment_author.
"""
from __future__ import annotations

from typing import Any


def list_page(
    client,
    workspace_id: str,
    task_id: str,
    *,
    cursor: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """One page. Returns {'items': [...], 'next_cursor': str | None}."""
    params: dict[str, Any] = {}
    if cursor is not None:
        params["cursor"] = cursor
    if limit is not None:
        params["limit"] = limit
    return client.get(
        f"/v1/workspaces/{workspace_id}/tasks/{task_id}/comments",
        params=params or None,
    )


def list_all(
    client,
    workspace_id: str,
    task_id: str,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Walk every page. Returns a flat items list."""
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = list_page(client, workspace_id, task_id, cursor=cursor, limit=limit)
        items.extend(page["items"])
        cursor = page.get("next_cursor")
        if not cursor:
            return items


def create(client, workspace_id: str, task_id: str, *, body: str) -> dict[str, Any]:
    return client.post(
        f"/v1/workspaces/{workspace_id}/tasks/{task_id}/comments",
        json={"body": body},
    )


def update(
    client,
    workspace_id: str,
    task_id: str,
    comment_id: str,
    *,
    body: str,
) -> dict[str, Any]:
    return client.patch(
        f"/v1/workspaces/{workspace_id}/tasks/{task_id}/comments/{comment_id}",
        json={"body": body},
    )


def delete(
    client,
    workspace_id: str,
    task_id: str,
    comment_id: str,
) -> None:
    client.delete(
        f"/v1/workspaces/{workspace_id}/tasks/{task_id}/comments/{comment_id}"
    )
