from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.infra import db
from app.infra.repositories import audit_repo


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> dict:
    r = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert r.status_code == 201, r.text
    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert login.status_code == 200, login.text
    return {
        "id": r.json()["id"],
        "email": email,
        "token": login.json()["access_token"],
    }


async def _make_ws(client: AsyncClient, token: str) -> str:
    r = await client.post(
        "/v1/workspaces", json={"name": "act-ws"}, headers=_auth(token)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _add_member(
    client: AsyncClient, admin_tok: str, ws: str, email: str, role: str
) -> None:
    r = await client.post(
        f"/v1/workspaces/{ws}/members",
        json={"email": email, "role": role},
        headers=_auth(admin_tok),
    )
    assert r.status_code == 201, r.text


async def _real_events(client: AsyncClient, token: str, ws: str) -> None:
    t = await client.post(
        f"/v1/workspaces/{ws}/tasks",
        json={"title": "act-task", "status": "todo"},
        headers=_auth(token),
    )
    tid = t.json()["id"]
    await client.post(
        f"/v1/workspaces/{ws}/tasks/{tid}/comments",
        json={"body": "real comment"},
        headers=_auth(token),
    )
    d = await client.delete(
        f"/v1/workspaces/{ws}/tasks/{tid}", headers=_auth(token)
    )
    assert d.status_code == 204


async def _inject_workspace_scoped_security_event(
    ws: str, action: str
) -> None:
    async for s in db.get_db():
        await audit_repo.record(
            s,
            actor_user_id=None,
            workspace_id=ws,
            action=action,
            target_type="x",
            target_id=uuid4(),
            payload={},
        )
        await s.commit()
        break


async def _scene(client: AsyncClient):
    admin = await _register(client, f"act-{uuid4()}@example.com")
    member = await _register(client, f"act-{uuid4()}@example.com")
    viewer = await _register(client, f"act-{uuid4()}@example.com")
    ws = await _make_ws(client, admin["token"])
    await _add_member(client, admin["token"], ws, member["email"], "member")
    await _add_member(client, admin["token"], ws, viewer["email"], "viewer")
    return admin, member, viewer, ws


async def test_member_and_viewer_can_read_activity(
    client: AsyncClient,
) -> None:
    admin, member, viewer, ws = await _scene(client)
    for tok in (member["token"], viewer["token"]):
        r = await client.get(
            f"/v1/workspaces/{ws}/activity", headers=_auth(tok)
        )
        assert r.status_code == 200, r.text


async def test_feed_shows_real_allowlisted_events(
    client: AsyncClient,
) -> None:
    admin, member, viewer, ws = await _scene(client)
    await _real_events(client, admin["token"], ws)

    r = await client.get(
        f"/v1/workspaces/{ws}/activity?limit=100",
        headers=_auth(member["token"]),
    )
    assert r.status_code == 200
    actions = {i["action"] for i in r.json()["items"]}
    # emitted + allowlisted events surface
    assert "workspace.created" in actions
    assert "member.invited" in actions
    assert "comment.created" in actions
    assert "task.deleted" in actions


async def test_security_events_never_in_feed(
    client: AsyncClient,
) -> None:
    admin, member, viewer, ws = await _scene(client)
    await _real_events(client, admin["token"], ws)

    for action in (
        "auth.refresh_reuse_detected",
        "auth.logged_out",
        "user.logged_in",
        "user.registered",
    ):
        await _inject_workspace_scoped_security_event(ws, action)

    r = await client.get(
        f"/v1/workspaces/{ws}/activity?limit=100",
        headers=_auth(member["token"]),
    )
    assert r.status_code == 200
    actions = {i["action"] for i in r.json()["items"]}

    assert not any(a.startswith("auth.") for a in actions), actions
    assert not any(a.startswith("user.") for a in actions), actions
    assert "comment.created" in actions
    assert "task.deleted" in actions


async def test_non_member_gets_404(client: AsyncClient) -> None:
    admin, member, viewer, ws = await _scene(client)
    outsider = await _register(client, f"act-{uuid4()}@example.com")
    r = await client.get(
        f"/v1/workspaces/{ws}/activity", headers=_auth(outsider["token"])
    )
    assert r.status_code == 404


async def test_ghost_workspace_404(client: AsyncClient) -> None:
    admin = await _register(client, f"act-{uuid4()}@example.com")
    r = await client.get(
        f"/v1/workspaces/{uuid4()}/activity",
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 404


async def test_malformed_cursor_400(client: AsyncClient) -> None:
    admin, member, viewer, ws = await _scene(client)
    r = await client.get(
        f"/v1/workspaces/{ws}/activity?cursor=not-valid",
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_cursor"


async def test_keyset_paginates_no_overlap(client: AsyncClient) -> None:
    admin, member, viewer, ws = await _scene(client)
    for _ in range(7):
        await _real_events(client, admin["token"], ws)

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        url = f"/v1/workspaces/{ws}/activity?limit=3"
        if cursor:
            url += f"&cursor={cursor}"
        r = await client.get(url, headers=_auth(admin["token"]))
        assert r.status_code == 200
        b = r.json()
        seen.extend(i["id"] for i in b["items"])
        cursor = b["next_cursor"]
        pages += 1
        if cursor is None:
            break
        assert pages < 20

    assert len(seen) == len(set(seen))  
