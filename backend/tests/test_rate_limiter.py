
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from redis import Redis
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.infra.rate_limiter import limiter, rate_limit_exceeded_handler


def _redis_client_db1() -> Redis:
    from urllib.parse import urlparse
    p = urlparse(get_settings().redis_url)
    host = p.hostname or "localhost"
    port = p.port or 6379
    return Redis(host=host, port=port, db=1)


@pytest.fixture
def fresh_limiter_db():
    r = _redis_client_db1()
    r.flushdb()
    yield r
    r.flushdb()


def _build_limited_app() -> FastAPI:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/limited")
    @limiter.limit("3/minute")
    async def limited(request: Request) -> dict:
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_first_three_requests_succeed(fresh_limiter_db) -> None:
    app = _build_limited_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for i in range(3):
            r = await ac.get("/limited")
            assert r.status_code == 200, f"request {i + 1}: {r.text}"


@pytest.mark.asyncio
async def test_fourth_request_returns_unified_429(fresh_limiter_db) -> None:
    app = _build_limited_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for _ in range(3):
            await ac.get("/limited")

        rejected = await ac.get("/limited")
        assert rejected.status_code == 429, rejected.text
        body = rejected.json()
        assert body == {
            "detail": {
                "detail": "rate limit exceeded",
                "code": "rate_limit_exceeded",
            },
        }


@pytest.mark.asyncio
async def test_limiter_state_persists_in_redis_db1(fresh_limiter_db) -> None:
    app = _build_limited_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get("/limited")

    keys = fresh_limiter_db.keys("*")
    assert len(keys) > 0, "limiter wrote nothing to redis db=1"
