
import asyncio                            
from typing import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.infra import db
from app.main import app

from redis import Redis

@pytest_asyncio.fixture(scope="session") 
def event_loop():                       
    loop = asyncio.new_event_loop()        
    yield loop               
    loop.close()           


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _engine_lifespan() -> AsyncIterator[None]:
    db.init_engine()
    yield
    await db.dispose_engine()

def _flush_limiter_db() -> None:
    from urllib.parse import urlparse
    from app.core.config import get_settings
    p = urlparse(get_settings().redis_url)
    Redis(host=p.hostname or "localhost", port=p.port or 6379, db=1).flushdb()


@pytest_asyncio.fixture(autouse=True)
async def _fresh_limiter_state() -> AsyncIterator[None]:
    _flush_limiter_db()
    yield
    _flush_limiter_db()

@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
