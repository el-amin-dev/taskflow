"""Task API client. Functions wrap one HTTP call each.

Backend: GET/POST /v1/workspaces/{ws}/tasks, PATCH/DELETE on /{task_id}.
No GET single (tracked: backend #105). No assignee filter (tracked: backend #106).
"""
from __future__ import annotations

from typing import Any


def list_all(client, workspace_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
    params = {"status": status} if status else None
    return client.get(f"/v1/workspaces/{workspace_id}/tasks", params=params)


def create(
    client,
    workspace_id: str,
    *,
    title: str,
    description: str | None = None,
    status: str | None = None,
    assignee_id: str | None = None,
    deadline: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"title": title}
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if assignee_id is not None:
        body["assignee_id"] = assignee_id
    if deadline is not None:
        body["deadline"] = deadline
    return client.post(f"/v1/workspaces/{workspace_id}/tasks", json=body)


def update(
    client,
    workspace_id: str,
    task_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    assignee_id: str | None = None,
    deadline: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if assignee_id is not None:
        body["assignee_id"] = assignee_id
    if deadline is not None:
        body["deadline"] = deadline
    return client.patch(f"/v1/workspaces/{workspace_id}/tasks/{task_id}", json=body)


def change_status(client, workspace_id: str, task_id: str, *, status: str) -> dict[str, Any]:
    """Thin wrapper around update() for the high-frequency status-change path."""
    return update(client, workspace_id, task_id, status=status)


def delete(client, workspace_id: str, task_id: str) -> None:
    client.delete(f"/v1/workspaces/{workspace_id}/tasks/{task_id}")
