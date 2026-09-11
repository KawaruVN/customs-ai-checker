from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from customs_ai.api import routes
from customs_ai.config import settings
from customs_ai.logger import logger
from customs_ai.repositories.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting %s in %s mode.",
        settings.app_name,
        settings.environment,
    )
    # Startup intentionally fails if SQLite cannot be initialized.
    init_db()
    yield
    logger.info("Shutting down %s.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(routes.router)
