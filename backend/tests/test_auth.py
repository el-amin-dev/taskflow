from httpx import AsyncClient

from uuid import uuid4



def _unique_email() -> str :
    return f"user-{uuid4()}@example.com"

async def test_register_happy_path (client : AsyncClient) -> None:
    email= _unique_email()
    
    response = await client.post(
        "/v1/auth/register",
        json={"email":email,"password":"his_password"}
    )
    assert response.status_code == 201 , response.text
    body = response.json()
    assert body["email"] == email
    assert body["role"] == "member"
    assert "id" in body
    assert "hashed_password" not in body


async def test_register_duplicate_returns_400(client:AsyncClient)-> None:
    email= _unique_email()
    payload= {"email":email , "password":"his_password"}

    first =await client.post(
        "/v1/auth/register",
        json=payload
    )
    
    assert first.status_code == 201 , first.text

    second =await client.post(
        "/v1/auth/register",
        json=payload
    )    

    assert second.status_code == 400
    assert second.json() == {"detail": {"detail": "could not create account", "code": "email_unavailable"}}
    assert email not in second.text

async def _register_and_login(
    client: AsyncClient,
    email: str,
    password: str,
) -> str:
    """register a fresh user and return a valid access token.
    helper for tests that need an authenticated client."""
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
    return login.json()["access_token"]


async def test_login_happy_path(client: AsyncClient) -> None:
    email = _unique_email()
    password = "correct-password"
    
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    
    response = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60  
    assert len(body["access_token"].split(".")) == 3


async def test_login_wrong_password(client: AsyncClient) -> None:
    email = _unique_email()
    
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert reg.status_code == 201
    
    response = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "WRONG"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": {"detail": "invalid email or password", "code": "invalid_credentials"}
    }


async def test_login_unknown_email_same_response_as_wrong_password(
    client: AsyncClient,
) -> None:
    """OWASP A07 — no email enumeration. Same body for any auth failure."""
    email = _unique_email()
    
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert reg.status_code == 201
    
    wrong_pw = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "WRONG"},
    )
    unknown_email = await client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "any"},
    )
    
    assert wrong_pw.status_code == unknown_email.status_code == 401
    assert wrong_pw.json() == unknown_email.json()
    assert email not in unknown_email.text  


async def test_me_with_valid_token(client: AsyncClient) -> None:
    email = _unique_email()
    token = await _register_and_login(client, email, "correct-password")
    
    response = await client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == email
    assert body["role"] == "member"
    assert "id" in body
    assert "hashed_password" not in body 


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/v1/auth/me")
    assert response.status_code == 401
    assert response.json() == {
        "detail": {"detail": "authentication required", "code": "invalid_token"}
    }
    assert response.headers.get("www-authenticate") == "Bearer"