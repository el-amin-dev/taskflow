import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging


log = logging.getLogger("taskflow.main")

_settings = get_settings()
setup_logging(_settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncIterator[None]:
    settings = get_settings()

    log.info("startup",extra={"env":settings.environment.value,"app":settings.app_name})
    yield
    log.info('shutdown')



def create_app() -> FastAPI:
    settings=get_settings()
    app = FastAPI(title=settings.app_name,lifespan=lifespan)

    @app.get("/health",tags=["meta"])
    async def health() -> dict[str, str ]:
        return {"status":"ok" , "service" : settings.app_name}
    return app

app = create_app()