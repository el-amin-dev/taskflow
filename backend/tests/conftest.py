
import asyncio                            
from typing import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.infra import db
from app.main import app


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


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
