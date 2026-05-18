
from uuid import uuid4

import pytest
from httpx import AsyncClient


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
        "/v1/workspaces", json={"name": "cmt-ws"}, headers=_auth(token)
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


async def _make_task(client: AsyncClient, token: str, ws: str) -> str:
    r = await client.post(
        f"/v1/workspaces/{ws}/tasks",
        json={"title": "cmt-task", "status": "todo"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _post(
    client: AsyncClient, token: str, ws: str, task: str, body: str
) -> dict:
    r = await client.post(
        f"/v1/workspaces/{ws}/tasks/{task}/comments",
        json={"body": body},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _scene(client: AsyncClient):
    admin = await _register(client, f"cmt-{uuid4()}@example.com")
    member = await _register(client, f"cmt-{uuid4()}@example.com")
    viewer = await _register(client, f"cmt-{uuid4()}@example.com")
    ws = await _make_ws(client, admin["token"])
    await _add_member(client, admin["token"], ws, member["email"], "member")
    await _add_member(client, admin["token"], ws, viewer["email"], "viewer")
    task = await _make_task(client, admin["token"], ws)
    return admin, member, viewer, ws, task


async def test_member_and_viewer_can_comment(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)

    m = await _post(client, member["token"], ws, task, "from member")
    v = await _post(client, viewer["token"], ws, task, "from viewer")
    assert m["body"] == "from member"
    assert v["body"] == "from viewer"
    assert m["created_at"] == m["updated_at"]


async def test_list_is_oldest_first_and_keyset_paginates(
    client: AsyncClient,
) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    for i in range(5):
        await _post(client, member["token"], ws, task, f"c{i}")

    seen: list[str] = []
    bodies: list[str] = []
    cursor = None
    pages = 0
    while True:
        url = f"/v1/workspaces/{ws}/tasks/{task}/comments?limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        r = await client.get(url, headers=_auth(member["token"]))
        assert r.status_code == 200, r.text
        b = r.json()
        seen.extend(c["id"] for c in b["items"])
        bodies.extend(c["body"] for c in b["items"])
        cursor = b["next_cursor"]
        pages += 1
        if cursor is None:
            break
        assert pages < 20

    assert len(seen) == 5
    assert len(set(seen)) == 5
    assert bodies == ["c0", "c1", "c2", "c3", "c4"]  


async def test_terminal_page_null_cursor(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    await _post(client, member["token"], ws, task, "only one")
    r = await client.get(
        f"/v1/workspaces/{ws}/tasks/{task}/comments?limit=50",
        headers=_auth(member["token"]),
    )
    assert r.status_code == 200
    assert r.json()["next_cursor"] is None


async def test_author_can_edit_own(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    c = await _post(client, member["token"], ws, task, "original")
    r = await client.patch(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{c['id']}",
        json={"body": "edited"},
        headers=_auth(member["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["body"] == "edited"


async def test_admin_cannot_edit_others_comment(
    client: AsyncClient,
) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    c = await _post(client, member["token"], ws, task, "members words")
    r = await client.patch(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{c['id']}",
        json={"body": "admin tampering"},
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "not_comment_author"


async def test_author_and_admin_can_delete(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    own = await _post(client, member["token"], ws, task, "member deletes this")
    mod = await _post(client, member["token"], ws, task, "admin moderates this")

    
    r1 = await client.delete(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{own['id']}",
        headers=_auth(member["token"]),
    )
    assert r1.status_code == 204

    r2 = await client.delete(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{mod['id']}",
        headers=_auth(admin["token"]),
    )
    assert r2.status_code == 204

    lst = await client.get(
        f"/v1/workspaces/{ws}/tasks/{task}/comments?limit=50",
        headers=_auth(member["token"]),
    )
    ids = {c["id"] for c in lst.json()["items"]}
    assert own["id"] not in ids
    assert mod["id"] not in ids


async def test_viewer_cannot_delete_others(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    c = await _post(client, member["token"], ws, task, "members comment")
    r = await client.delete(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{c['id']}",
        headers=_auth(viewer["token"]),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "not_comment_author"


async def test_non_member_gets_404_not_403(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    c = await _post(client, member["token"], ws, task, "inside")
    outsider = await _register(client, f"cmt-{uuid4()}@example.com")

    edit = await client.patch(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{c['id']}",
        json={"body": "x"},
        headers=_auth(outsider["token"]),
    )
    assert edit.status_code == 404


async def test_malformed_cursor_400(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    r = await client.get(
        f"/v1/workspaces/{ws}/tasks/{task}/comments?cursor=not-valid",
        headers=_auth(member["token"]),
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_cursor"


async def test_empty_body_rejected(client: AsyncClient) -> None:
    admin, member, viewer, ws, task = await _scene(client)
    r = await client.post(
        f"/v1/workspaces/{ws}/tasks/{task}/comments",
        json={"body": ""},
        headers=_auth(member["token"]),
    )
    assert r.status_code == 422


async def test_comment_events_in_audit_trail(client: AsyncClient) -> None:
    
    admin, member, viewer, ws, task = await _scene(client)
    c = await _post(client, member["token"], ws, task, "audit me")
    await client.delete(
        f"/v1/workspaces/{ws}/tasks/{task}/comments/{c['id']}",
        headers=_auth(admin["token"]),  
    )

    r = await client.get(
        f"/v1/workspaces/{ws}/audit?limit=100",
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    actions = [i["action"] for i in items]
    assert "comment.created" in actions
    assert "comment.deleted" in actions

    deleted = next(i for i in items if i["action"] == "comment.deleted")
    assert deleted["payload"]["was_author"] is False  
