from uuid import uuid4

from httpx import AsyncClient


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


async def _register_and_login(client: AsyncClient, email: str, password: str = "correct-password") -> dict:

    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]

    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    return {"email": email, "token": token, "id": user_id}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_workspace_with_roles(client: AsyncClient) -> dict:
    admin = await _register_and_login(client, _unique_email("ws-admin"))
    member = await _register_and_login(client, _unique_email("ws-member"))
    viewer = await _register_and_login(client, _unique_email("ws-viewer"))
    outsider = await _register_and_login(client, _unique_email("ws-outsider"))

    ws_resp = await client.post(
        "/v1/workspaces",
        json={"name": "engineering"},
        headers=_auth(admin["token"]),
    )
    assert ws_resp.status_code == 201, ws_resp.text
    workspace_id = ws_resp.json()["id"]

    invite_m = await client.post(
        f"/v1/workspaces/{workspace_id}/members",
        json={"email": member["email"], "role": "member"},
        headers=_auth(admin["token"]),
    )
    assert invite_m.status_code == 201, invite_m.text

    invite_v = await client.post(
        f"/v1/workspaces/{workspace_id}/members",
        json={"email": viewer["email"], "role": "viewer"},
        headers=_auth(admin["token"]),
    )
    assert invite_v.status_code == 201, invite_v.text

    return {
        "workspace_id": workspace_id,
        "admin": admin,
        "member": member,
        "viewer": viewer,
        "outsider": outsider,
    }


async def test_create_workspace_makes_creator_admin(client: AsyncClient) -> None:
    alice = await _register_and_login(client, _unique_email("ws-create"))

    response = await client.post(
        "/v1/workspaces",
        json={"name": "engineering"},
        headers=_auth(alice["token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "engineering"
    assert body["owner_id"] == alice["id"]

    listing = await client.get("/v1/workspaces", headers=_auth(alice["token"]))
    assert listing.status_code == 200
    assert any(w["id"] == body["id"] for w in listing.json())


async def test_list_workspaces_shows_only_mine(client: AsyncClient) -> None:
    alice = await _register_and_login(client, _unique_email("ws-alice"))
    bob = await _register_and_login(client, _unique_email("ws-bob"))

    ws = await client.post(
        "/v1/workspaces",
        json={"name": "alice's space"},
        headers=_auth(alice["token"]),
    )
    assert ws.status_code == 201

    bob_listing = await client.get("/v1/workspaces", headers=_auth(bob["token"]))
    assert bob_listing.status_code == 200
    assert bob_listing.json() == []  


async def test_admin_invites_member_201(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)
    new_user = await _register_and_login(client, _unique_email("ws-newinv"))

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": new_user["email"], "role": "member"},
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == new_user["id"]
    assert body["role"] == "member"


async def test_invite_duplicate_returns_409_already_member(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": ctx["member"]["email"], "role": "member"},
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "already_member"


async def test_invite_unknown_email_returns_404_user_not_found(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": "nobody@example.com", "role": "member"},
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


async def test_member_cannot_invite_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)
    target = await _register_and_login(client, _unique_email("ws-target"))

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": target["email"], "role": "member"},
        headers=_auth(ctx["member"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


async def test_viewer_cannot_invite_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)
    target = await _register_and_login(client, _unique_email("ws-target"))

    response = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": target["email"], "role": "member"},
        headers=_auth(ctx["viewer"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


async def test_outsider_workspace_response_byte_identical_to_nonmember(
    client: AsyncClient,
) -> None:
    """OWASP A01 — a complete outsider, an insider-but-not-admin, and a
    nonexistent workspace all get the SAME response. The byte-identity is
    the contract that prevents workspace enumeration."""
    ctx = await _setup_workspace_with_roles(client)
    target = await _register_and_login(client, _unique_email("ws-target"))

    outsider_resp = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": target["email"], "role": "member"},
        headers=_auth(ctx["outsider"]["token"]),
    )

    viewer_resp = await client.post(
        f"/v1/workspaces/{ctx['workspace_id']}/members",
        json={"email": target["email"], "role": "member"},
        headers=_auth(ctx["viewer"]["token"]),
    )

    ghost_resp = await client.post(
        f"/v1/workspaces/{uuid4()}/members",
        json={"email": target["email"], "role": "member"},
        headers=_auth(ctx["admin"]["token"]),
    )

    assert outsider_resp.status_code == 404
    assert viewer_resp.status_code == 404
    assert ghost_resp.status_code == 404

    assert outsider_resp.json() == viewer_resp.json() == ghost_resp.json()


async def test_admin_removes_member_204(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.delete(
        f"/v1/workspaces/{ctx['workspace_id']}/members/{ctx['member']['id']}",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 204
    assert response.content == b"" 

async def test_cannot_remove_owner_returns_409(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.delete(
        f"/v1/workspaces/{ctx['workspace_id']}/members/{ctx['admin']['id']}",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cannot_remove_owner"


async def test_remove_nonmember_returns_404(client: AsyncClient) -> None:
    """removing a user who isn't in the workspace returns member_not_found,
    not workspace_not_found — admin DOES have access, target doesn't exist as
    a member here."""
    ctx = await _setup_workspace_with_roles(client)
    ghost = await _register_and_login(client, _unique_email("ws-ghost"))

    response = await client.delete(
        f"/v1/workspaces/{ctx['workspace_id']}/members/{ghost['id']}",
        headers=_auth(ctx["admin"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "member_not_found"


async def test_member_cannot_remove_returns_404(client: AsyncClient) -> None:
    ctx = await _setup_workspace_with_roles(client)

    response = await client.delete(
        f"/v1/workspaces/{ctx['workspace_id']}/members/{ctx['viewer']['id']}",
        headers=_auth(ctx["member"]["token"]),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"
