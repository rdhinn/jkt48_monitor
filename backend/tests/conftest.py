"""Shared pytest fixtures using an in-memory SQLite database."""
from __future__ import annotations

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_factory(db_engine):
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(db_factory):
    async with db_factory() as session:
        from app.db.init_db import ensure_default_user

        await ensure_default_user(session)
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def client(db_factory):
    from app.db.init_db import ensure_default_user

    async def override_get_session():
        async with db_factory() as session:
            yield session

    async with db_factory() as boot:
        await ensure_default_user(boot)
        await boot.commit()

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def telegram_enabled(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "telegram_notify_max_retries", 2)
    yield settings


@pytest_asyncio.fixture
def reset_monitor():
    from app.services.monitor import monitor

    monitor._manual_times.clear()
    yield
    monitor._manual_times.clear()