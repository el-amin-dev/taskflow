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
    assert second.json() == {"detail": "could not create account"}
    assert email not in second.text
