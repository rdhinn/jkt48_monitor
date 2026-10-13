"""Source-check audit queries."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SourceCheck


async def record(
    db: AsyncSession,
    *,
    source_name: str,
    endpoint_name: str,
    success: bool,
    response_status: int | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> SourceCheck:
    check = SourceCheck(
        source_name=source_name,
        endpoint_name=endpoint_name,
        success=success,
        response_status=response_status,
        error_message=(error_message or None) and error_message[:2000],
        duration_ms=duration_ms,
    )
    db.add(check)
    await db.flush()
    return check


async def recent(db: AsyncSession, limit: int = 50) -> list[SourceCheck]:
    stmt = select(SourceCheck).order_by(SourceCheck.checked_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def latest_by_source(db: AsyncSession) -> dict[str, SourceCheck]:
    stmt = select(SourceCheck).order_by(SourceCheck.checked_at.desc())
    result = {}
    for check in (await db.execute(stmt)).scalars().all():
        result.setdefault(check.source_name, check)
    return result


async def latest_success_by_source(db: AsyncSession) -> dict[str, SourceCheck]:
    stmt = (
        select(SourceCheck)
        .where(SourceCheck.success.is_(True))
        .order_by(SourceCheck.checked_at.desc())
    )
    result = {}
    for check in (await db.execute(stmt)).scalars().all():
        result.setdefault(check.source_name, check)
    return result
