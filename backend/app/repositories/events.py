"""Event and session queries."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Event, EventSession, Member


async def list_events(
    db: AsyncSession,
    *,
    q: str | None = None,
    entry_type: str | None = None,
    category: str | None = None,
    active_only: bool = False,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Event], int]:
    stmt: Select = select(Event)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Event.name).like(like),
                func.lower(Event.external_id).like(like),
            )
        )
    if entry_type:
        stmt = stmt.where(Event.entry_type == entry_type)
    if category:
        stmt = stmt.where(Event.category == category)
    if active_only:
        stmt = stmt.where(Event.is_active.is_(True))
    if date_from:
        stmt = stmt.where(or_(Event.starts_at.is_(None), Event.starts_at >= date_from))
    if date_to:
        stmt = stmt.where(or_(Event.starts_at.is_(None), Event.starts_at <= date_to))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        stmt.options(selectinload(Event.sessions))
        .order_by(Event.starts_at.asc().nulls_last(), Event.name.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), int(total)


async def get_event(db: AsyncSession, event_id: int) -> Event | None:
    stmt = (
        select(Event)
        .options(selectinload(Event.sessions))
        .where(Event.id == event_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_event_by_external(db: AsyncSession, external_id: str) -> Event | None:
    stmt = (
        select(Event)
        .options(selectinload(Event.sessions))
        .where(Event.external_id == external_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_upcoming_sessions(db: AsyncSession, limit: int = 100) -> list[EventSession]:
    stmt = (
        select(EventSession)
        .options(selectinload(EventSession.event))
        .order_by(EventSession.starts_at.asc().nulls_last())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
