"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.init_db import create_tables, ensure_admin_user
from app.services.monitor import monitor

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging("DEBUG" if settings.debug else "INFO")
    logger.info("Starting %s", settings.app_name)
    await create_tables()
    await ensure_admin_user()

    from app.db.session import SessionLocal
    from app.scheduler.telegram_worker import telegram_worker

    if settings.enable_scheduler:
        await monitor.start_background(SessionLocal)
    await telegram_worker.start()

    try:
        yield
    finally:
        await monitor.stop_background()
        await telegram_worker.stop()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Dashboard backend for monitoring JKT48 ticket availability (Video Call, "
        "Meet & Greet, 2-Shot). Live ticket data is provided by the 48pedia.id "
        "Public API when JKT48_API_KEY is configured."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api": "/api/v1",
        "source_configured": settings.api_key_configured,
    }
