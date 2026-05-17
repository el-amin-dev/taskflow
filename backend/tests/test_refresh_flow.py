from uuid import uuid4

import pytest
import pytest_asyncio
import redis
from httpx import AsyncClient

from app.infra.refresh_store import _store_url


@pytest.fixture(autouse=True)
def _fresh_refresh_store():
    r = redis.Redis.from_url(_store_url(), decode_responses=True)
    r.flushdb()
    yield
    r.flushdb()


async def _register_and_login(client: AsyncClient, email: str) -> dict:
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
    body = login.json()
    return {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
    }


async def test_login_issues_refresh_token(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, f"rf-{uuid4()}@example.com")
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["access_token"] != tokens["refresh_token"]


async def test_refresh_rotates_and_retires_old(client: AsyncClient) -> None:
    t = await _register_and_login(client, f"rf-{uuid4()}@example.com")
    old_rt = t["refresh_token"]

    r = await client.post(
        "/v1/auth/refresh", json={"refresh_token": old_rt}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    new_rt = body["refresh_token"]

    assert new_rt
    assert new_rt != old_rt
    assert body["access_token"]

    replay = await client.post(
        "/v1/auth/refresh", json={"refresh_token": old_rt}
    )
    assert replay.status_code == 401, replay.text

