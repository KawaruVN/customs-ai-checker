from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from customs_ai.api.routes import health
from customs_ai.config import settings
from customs_ai.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting %s in %s mode.",
        settings.app_name,
        settings.environment,
    )
    yield
    logger.info("Shutting down %s.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)

