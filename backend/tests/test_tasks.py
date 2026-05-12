from uuid import uuid4

from httpx import AsyncClient


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "correct-password"
) -> dict:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {
        "email": email,
        "token": login.json()["access_token"],
        "id": reg.json()["id"],
    }


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_workspace_with_roles(client: AsyncClient) -> dict:
    admin = await _register_and_login(client, _unique_email("tk-admin"))
    member = await _register_and_login(client, _unique_email("tk-member"))
    viewer = await _register_and_login(client, _unique_email("tk-viewer"))
    outsider = await _register_and_login(client, _unique_email("tk-outsider"))

    ws = await client.post(
        "/v1/workspaces",
        json={"name": "engineering"},
        headers=_auth(admin["token"]),
    )
    assert ws.status_code == 201
    workspace_id = ws.json()["id"]

    invite_m = await client.post(
        f"/v1/workspaces/{workspace_id}/members",
        json={"email": member["email"], "role": "member"},
        headers=_auth(admin["token"]),
    )
    assert invite_m.status_code == 201

    invite_v = await client.post(
        f"/v1/workspaces/{workspace_id}/members",
        json={"email": viewer["email"], "role": "viewer"},
        headers=_auth(admin["token"]),
    )
    assert invite_v.status_code == 201

    return {
        "workspace_id": workspace_id,
        "admin": admin, "member": member,
        "viewer": viewer, "outsider": outsider,
    }


async def test_admin_creates_task_201(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={"title": "write design doc"},
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "write design doc"
    assert body["status"] == "todo"  # default
    assert body["created_by"] == ctx["admin"]["id"]
    assert body["workspace_id"] == ctx["workspace_id"]


async def test_member_creates_task_201(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={
            "title": "ship q3",
            "description": "see linear",
            "status": "in_progress",
        },
        headers=_auth(ctx["member"]["token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["description"] == "see linear"
    assert body["created_by"] == ctx["member"]["id"]


async def test_viewer_cannot_create_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={"title": "viewer cannot create"},
        headers=_auth(ctx["viewer"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


async def test_outsider_cannot_create_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={"title": "outsider cannot create"},
        headers=_auth(ctx["outsider"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


async def test_creation_404_byte_identical_across_blocked_callers(
    client: AsyncClient,
) -> None:
    ctx = await _setup_workspace_with_roles(client)
    payload = {"title": "irrelevant"}

    viewer_resp = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json=payload,
        headers=_auth(ctx["viewer"]["token"]),
    )
    outsider_resp = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json=payload,
        headers=_auth(ctx["outsider"]["token"]),
    )
    ghost_resp = await client.post(
        f"/v1/workspaces/{uuid4()}/tasks",
        json=payload,
        headers=_auth(ctx["admin"]["token"]),
    )

    assert viewer_resp.status_code == 404
    assert outsider_resp.status_code == 404
    assert ghost_resp.status_code == 404
    # byte-identical: an attacker cannot distinguish these three states
    assert viewer_resp.json() == outsider_resp.json() == ghost_resp.json()


async def test_all_members_can_list_including_viewer(
    client: AsyncClient,
) -> None:
    ctx = await _setup_workspace_with_roles(client)

    # admin creates two tasks
    for title, status_ in [("task one", "todo"), ("task two", "in_progress")]:
        r = await client.post(
            f"/v1/workspaces/{ctx['workspace_id']}/tasks",
            json={"title": title, "status": status_},
            headers=_auth(ctx["admin"]["token"]),
        )
        assert r.status_code == 201

    # all three internal roles can list
    for role_label in ["admin", "member", "viewer"]:
        listing = await client.get(
            f"/v1/workspaces/{ctx['workspace_id']}/tasks",
            headers=_auth(ctx[role_label]["token"]),
        )
        assert listing.status_code == 200, f"{role_label}: {listing.text}"
        assert len(listing.json()) == 2, f"{role_label} count mismatch"


async def test_outsider_cannot_list_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.get(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        headers=_auth(ctx["outsider"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


async def test_list_with_status_filter_returns_subset(
    client: AsyncClient,
) -> None:
    ctx = await _setup_workspace_with_roles(client)

    # 2 todos, 1 in_progress
    for title in ["todo-a", "todo-b"]:
        await client.post(
            f"/v1/workspaces/{ctx['workspace_id']}/tasks",
            json={"title": title, "status": "todo"},
            headers=_auth(ctx["admin"]["token"]),
        )
    await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={"title": "in-prog", "status": "in_progress"},
        headers=_auth(ctx["admin"]["token"]),
    )

    todo_listing = await client.get(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks?status=todo",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert todo_listing.status_code == 200
    todos = todo_listing.json()
    assert len(todos) == 2
    assert all(t["status"] == "todo" for t in todos)

    ip_listing = await client.get(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks?status=in_progress",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert ip_listing.status_code == 200
    assert len(ip_listing.json()) == 1

    done_listing = await client.get(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks?status=done",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert done_listing.status_code == 200
    assert done_listing.json() == []


async def test_invalid_status_filter_returns_422(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.get(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks?status=garbage",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 422


async def test_empty_title_returns_422(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/tasks",
        json={"title": ""},
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 422
