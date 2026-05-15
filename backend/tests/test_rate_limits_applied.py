
import pytest
from httpx import AsyncClient
from redis import Redis

from app.core.config import get_settings




async def _register_unique(client: AsyncClient) -> dict:
    from uuid import uuid4
    email = f"rl-{uuid4()}@example.com"
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert login.status_code == 200, login.text
    return {
        "email": email,
        "id": reg.json()["id"],
        "token": login.json()["access_token"],
    }


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_login_5th_request_succeeds_6th_returns_429(
    client: AsyncClient,
) -> None:
    payload = {"email": "nobody@example.com", "password": "x"}

    for i in range(5):
        r = await client.post("/v1/auth/login", json=payload)
        assert r.status_code == 401, f"attempt {i + 1}: {r.status_code} {r.text}"

    sixth = await client.post("/v1/auth/login", json=payload)
    assert sixth.status_code == 429, f"expected 429, got {sixth.status_code}: {sixth.text}"


async def test_429_body_is_unified_shape(client: AsyncClient) -> None:
    payload = {"email": "nobody@example.com", "password": "x"}
    for _ in range(5):
        await client.post("/v1/auth/login", json=payload)

    rejected = await client.post("/v1/auth/login", json=payload)
    assert rejected.status_code == 429
    assert rejected.json() == {
        "detail": {
            "detail": "rate limit exceeded",
            "code": "rate_limit_exceeded",
        },
    }


async def test_health_and_ready_are_unlimited(client: AsyncClient) -> None:
    for _ in range(30):
        r = await client.get("/health")
        assert r.status_code == 200, r.text


async def test_register_11th_request_returns_unified_429(
    client: AsyncClient,
) -> None:
    from uuid import uuid4

    for i in range(10):
        email = f"rl-burn-{uuid4()}@example.com"
        r = await client.post(
            "/v1/auth/register",
            json={"email": email, "password": "correct-password"},
        )
        assert r.status_code == 201, f"attempt {i + 1}: {r.text}"

    eleventh = await client.post(
        "/v1/auth/register",
        json={"email": f"rl-burn-{uuid4()}@example.com", "password": "correct-password"},
    )
    assert eleventh.status_code == 429, eleventh.text
    assert eleventh.json()["detail"]["code"] == "rate_limit_exceeded"


async def test_per_user_isolation_different_buckets(client: AsyncClient) -> None:
    alice = await _register_unique(client)
    bob = await _register_unique(client)

    r1 = await client.get("/v1/auth/me", headers=_auth(alice["token"]))
    r2 = await client.get("/v1/auth/me", headers=_auth(bob["token"]))
    assert r1.status_code == 200
    assert r2.status_code == 200

    from urllib.parse import urlparse
    p = urlparse(get_settings().redis_url)
    r = Redis(host=p.hostname or "localhost", port=p.port or 6379, db=1)
    keys = [k.decode() for k in r.keys("*")]

    me_keys = [k for k in keys if "/v1/auth/me" in k]
    user_buckets = [k for k in me_keys if f"user:{alice['id']}" in k or f"user:{bob['id']}" in k]

    assert len(user_buckets) == 2, f"expected 2 per-user /me buckets, got {len(user_buckets)}: {me_keys}"
