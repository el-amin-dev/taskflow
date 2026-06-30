"""Members API endpoints: invite only (list/remove blocked by backend #85)."""
from __future__ import annotations

from typing import Any

from taskflow_cli.transport import Client


def invite(
    client: Client,
    workspace_id: str,
    *,
    email: str,
    role: str,
) -> dict[str, Any]:
    """POST /v1/workspaces/{ws}/members -> MemberResponse."""
    return client.post(
        f"/v1/workspaces/{workspace_id}/members",
        json={"email": email, "role": role},
    )
