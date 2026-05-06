import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging

from app.api.meta import router as router_meta
from app.api.v1 import router as router_v1



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

    app.include_router(router=router_meta)
    app.include_router(router=router_v1)

    return app 

app = create_app()