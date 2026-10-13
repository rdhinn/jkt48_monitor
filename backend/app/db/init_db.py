"""Startup helpers: table creation, admin bootstrap, optional demo data."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import User

logger = get_logger(__name__)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_admin_user() -> None:
    async with SessionLocal() as db:
        stmt = select(User).where(User.username == settings.admin_username)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user is None:
            user = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            )
            db.add(user)
            await db.commit()
            logger.info("Seeded admin user '%s'", settings.admin_username)


async def ensure_default_user(db: AsyncSession) -> User:
    """Return the local single-user account used for favorites by default."""
    stmt = select(User).where(User.id == 1)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(user)
        await db.flush()
    return user
