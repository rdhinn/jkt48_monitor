"""Availability snapshot queries, including latest-per-session lookup."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AvailabilitySnapshot, Event, EventSession, Member


def latest_snapshot_subquery():
    ranked = (
        select(
            AvailabilitySnapshot.id.label("snap_id"),
            func.row_number()
            .over(
                partition_by=AvailabilitySnapshot.session_id,
                order_by=(
                    AvailabilitySnapshot.observed_at.desc(),
                    AvailabilitySnapshot.id.desc(),
                ),
            )
            .label("rn"),
        )
    ).subquery()
    return (
        select(AvailabilitySnapshot)
        .join(ranked, AvailabilitySnapshot.id == ranked.c.snap_id)
        .where(ranked.c.rn == 1)
    ).subquery()


def _apply_filters(
    stmt: Select,
    *,
    latest,
    category: str | None,
    status: str | None,
    entry_type: str | None,
    member_q: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    event_id: int | None,
    member_id: int | None,
    favorite_ids: set[int] | None,
    only_favorites: bool,
) -> Select:
    if category:
        stmt = stmt.where(EventSession.ticket_category == category)
    if status:
        stmt = stmt.where(latest.c.status == status)
    if entry_type:
        stmt = stmt.where(Event.entry_type == entry_type)
    if member_q:
        like = f"%{member_q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(func.coalesce(Member.name, "")).like(like),
                func.lower(func.coalesce(EventSession.session_label, "")).like(like),
            )
        )
    if date_from:
        stmt = stmt.where(or_(EventSession.starts_at.is_(None), EventSession.starts_at >= date_from))
    if date_to:
        stmt = stmt.where(or_(EventSession.starts_at.is_(None), EventSession.starts_at <= date_to))
    if event_id:
        stmt = stmt.where(EventSession.event_id == event_id)
    if member_id:
        stmt = stmt.where(EventSession.member_id == member_id)
    if only_favorites and favorite_ids is not None:
        if favorite_ids:
            stmt = stmt.where(EventSession.member_id.in_(favorite_ids))
        else:
            stmt = stmt.where(False)
    return stmt


def _base_select(latest):
    return (
        select(
            EventSession.id.label("session_id"),
            EventSession.event_id.label("event_id"),
            Event.external_id.label("event_external_id"),
            Event.name.label("event_name"),
            Event.entry_type.label("entry_type"),
            EventSession.ticket_category.label("ticket_category"),
            EventSession.session_label.label("session_label"),
            EventSession.session_number.label("session_number"),
            EventSession.starts_at.label("starts_at"),
            EventSession.member_id.label("member_id"),
            Member.name.label("member_name"),
            latest.c.status.label("status"),
            latest.c.tickets_remaining.label("tickets_remaining"),
            latest.c.total_quota.label("total_quota"),
            latest.c.source.label("source"),
            Event.source_url.label("source_url"),
            latest.c.observed_at.label("observed_at"),
            latest.c.source_updated_at.label("source_updated_at"),
        )
        .join(Event, EventSession.event_id == Event.id)
        .join(latest, latest.c.session_id == EventSession.id, isouter=True)
        .join(Member, EventSession.member_id == Member.id, isouter=True)
    )


async def list_availability(
    db: AsyncSession,
    *,
    category: str | None = None,
    status: str | None = None,
    entry_type: str | None = None,
    member_q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    event_id: int | None = None,
    member_id: int | None = None,
    favorite_ids: set[int] | None = None,
    only_favorites: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    latest = latest_snapshot_subquery()
    stmt = _base_select(latest)
    stmt = _apply_filters(
        stmt,
        latest=latest,
        category=category,
        status=status,
        entry_type=entry_type,
        member_q=member_q,
        date_from=date_from,
        date_to=date_to,
        event_id=event_id,
        member_id=member_id,
        favorite_ids=favorite_ids,
        only_favorites=only_favorites,
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        stmt.order_by(
            EventSession.starts_at.asc().nulls_last(),
            Event.name.asc(),
            EventSession.session_number.asc().nulls_last(),
        )
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).mappings().all()
    return [dict(row) for row in rows], int(total)


async def get_availability_row(db: AsyncSession, session_id: int) -> dict | None:
    latest = latest_snapshot_subquery()
    stmt = _base_select(latest).where(EventSession.id == session_id)
    row = (await db.execute(stmt)).mappings().first()
    return dict(row) if row else None


async def latest_snapshot(db: AsyncSession, session_id: int) -> AvailabilitySnapshot | None:
    stmt = (
        select(AvailabilitySnapshot)
        .where(AvailabilitySnapshot.session_id == session_id)
        .order_by(AvailabilitySnapshot.observed_at.desc(), AvailabilitySnapshot.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def history(
    db: AsyncSession,
    *,
    session_id: int | None = None,
    category: str | None = None,
    member_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    source: str | None = None,
    offset: int = 0,
    limit: int = 200,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            AvailabilitySnapshot.observed_at.label("observed_at"),
            AvailabilitySnapshot.status.label("status"),
            AvailabilitySnapshot.tickets_remaining.label("tickets_remaining"),
            AvailabilitySnapshot.sold_count.label("sold_count"),
            AvailabilitySnapshot.source.label("source"),
            AvailabilitySnapshot.session_id.label("session_id"),
            Member.name.label("member_name"),
            Event.name.label("event_name"),
        )
        .join(EventSession, AvailabilitySnapshot.session_id == EventSession.id)
        .join(Event, EventSession.event_id == Event.id)
        .join(Member, EventSession.member_id == Member.id, isouter=True)
    )
    if session_id:
        stmt = stmt.where(AvailabilitySnapshot.session_id == session_id)
    if category:
        stmt = stmt.where(EventSession.ticket_category == category)
    if member_id:
        stmt = stmt.where(EventSession.member_id == member_id)
    if source:
        stmt = stmt.where(AvailabilitySnapshot.source == source)
    if date_from:
        stmt = stmt.where(AvailabilitySnapshot.observed_at >= date_from)
    if date_to:
        stmt = stmt.where(AvailabilitySnapshot.observed_at <= date_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        stmt.order_by(AvailabilitySnapshot.observed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).mappings().all()
    return [dict(row) for row in rows], int(total)


async def recent_change_rows(db: AsyncSession, scan_limit: int = 600) -> list[dict]:
    stmt = (
        select(
            AvailabilitySnapshot.session_id,
            AvailabilitySnapshot.status,
            AvailabilitySnapshot.tickets_remaining,
            AvailabilitySnapshot.observed_at,
            AvailabilitySnapshot.source,
            Event.name.label("event_name"),
            EventSession.ticket_category,
            EventSession.session_number,
            Member.name.label("member_name"),
        )
        .join(EventSession, AvailabilitySnapshot.session_id == EventSession.id)
        .join(Event, EventSession.event_id == Event.id)
        .join(Member, EventSession.member_id == Member.id, isouter=True)
        .order_by(AvailabilitySnapshot.observed_at.desc(), AvailabilitySnapshot.id.desc())
        .limit(scan_limit)
    )
    rows = (await db.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]


async def declining_sessions(db: AsyncSession, scan_limit: int = 600) -> int:
    rows = await recent_change_rows(db, scan_limit)
    latest_remaining: dict[int, int | None] = {}
    compared: set[int] = set()
    declining = 0
    for row in rows:
        sid = row["session_id"]
        if sid not in latest_remaining:
            latest_remaining[sid] = row["tickets_remaining"]
            continue
        if sid in compared:
            continue
        compared.add(sid)
        prev = latest_remaining[sid]
        if (
            prev is not None
            and row["tickets_remaining"] is not None
            and row["tickets_remaining"] < prev
        ):
            declining += 1
    return declining


async def status_counts(db: AsyncSession) -> dict[str, int]:
    latest = latest_snapshot_subquery()
    stmt = select(latest.c.status, func.count()).group_by(latest.c.status)
    result = (await db.execute(stmt)).all()
    return {row[0] or "unknown": int(row[1]) for row in result}


async def category_counts(db: AsyncSession) -> dict[str, int]:
    latest = latest_snapshot_subquery()
    stmt = (
        select(EventSession.ticket_category, func.count())
        .join(latest, latest.c.session_id == EventSession.id, isouter=True)
        .where(latest.c.status == "available")
        .group_by(EventSession.ticket_category)
    )
    result = (await db.execute(stmt)).all()
    return {row[0]: int(row[1]) for row in result}


async def member_ids_matching(
    db: AsyncSession,
    *,
    event_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
) -> set[int]:
    latest = latest_snapshot_subquery()
    stmt = (
        select(EventSession.member_id)
        .join(latest, latest.c.session_id == EventSession.id, isouter=True)
        .where(EventSession.member_id.is_not(None))
    )
    if event_id:
        stmt = stmt.where(EventSession.event_id == event_id)
    if category:
        stmt = stmt.where(EventSession.ticket_category == category)
    if status:
        stmt = stmt.where(latest.c.status == status)
    rows = (await db.execute(stmt.distinct())).all()
    return {row[0] for row in rows if row[0] is not None}


async def member_availability_summary(
    db: AsyncSession, member_id: int
) -> dict:
    latest = latest_snapshot_subquery()
    stmt = (
        select(
            func.count(EventSession.id),
            func.sum(case((latest.c.status == "available", 1), else_=0)),
            func.sum(latest.c.tickets_remaining),
        )
        .join(latest, latest.c.session_id == EventSession.id, isouter=True)
        .where(EventSession.member_id == member_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return {"total_sessions": 0, "sessions_available": 0, "tickets_remaining": None}
    total = int(row[0] or 0)
    if total == 0:
        return await _member_summary_fallback(db, member_id)
    return {
        "total_sessions": total,
        "sessions_available": int(row[1] or 0),
        "tickets_remaining": int(row[2]) if row[2] is not None else None,
    }


async def _member_summary_fallback(db: AsyncSession, member_id: int) -> dict:
    latest = latest_snapshot_subquery()
    stmt = (
        select(latest.c.status, latest.c.tickets_remaining)
        .join(EventSession, latest.c.session_id == EventSession.id)
        .where(EventSession.member_id == member_id)
    )
    rows = (await db.execute(stmt)).all()
    available = sum(1 for r in rows if r[0] == "available")
    remaining_values = [r[1] for r in rows if r[1] is not None]
    return {
        "total_sessions": len(rows),
        "sessions_available": available,
        "tickets_remaining": sum(remaining_values) if remaining_values else None,
    }
