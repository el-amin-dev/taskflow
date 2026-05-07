import logging
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from sqlalchemy import text


from app.core.config import get_settings


log = logging.getLogger("taskflow.infra.db")

_engine : AsyncEngine | None  = None
_session_factory : async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None :
    global _engine , _session_factory 
    if _engine is not None:
        return
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug
    ) 

    _session_factory = async_sessionmaker(_engine , expire_on_commit=False)
    log.info("db engine initialized ")

async def dispose_engine() -> None : 
    global _engine , _session_factory
    if _engine is None:
        return
    await _engine.dispose()
    _engine = None
    _session_factory = None
    log.info("db engine disposed ")


async def get_db() -> AsyncIterator[AsyncEngine]:
    if _session_factory is None:
        raise RuntimeError("db engnine is not initialized  - call init_engine() first ")
    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()

async def db_ping() -> bool:
    if _engine is None:
        return False
    try:
        async with _engine.connect() as conn : 
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1 
    except Exception as e :
        log.warning("db ping failed " , extra={"error": str(e)})
        return False