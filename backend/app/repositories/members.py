"""Member queries."""
from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, Member


def _apply_filters(stmt: Select, q: str | None, team: str | None, generation: str | None,
                   active_only: bool) -> Select:
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Member.name).like(like),
                func.lower(func.coalesce(Member.nickname, "")).like(like),
                func.lower(Member.external_id).like(like),
            )
        )
    if team:
        stmt = stmt.where(Member.team_code == team)
    if generation:
        stmt = stmt.where(Member.generation_code == generation)
    if active_only:
        stmt = stmt.where(Member.is_active.is_(True))
    return stmt


async def list_members(
    db: AsyncSession,
    *,
    q: str | None = None,
    team: str | None = None,
    generation: str | None = None,
    active_only: bool = True,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Member], int]:
    base = select(Member)
    base = _apply_filters(base, q, team, generation, active_only)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = base.order_by(Member.name.asc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), int(total)


async def get_member(db: AsyncSession, member_id: int) -> Member | None:
    return await db.get(Member, member_id)


async def get_member_by_external(db: AsyncSession, external_id: str) -> Member | None:
    stmt = select(Member).where(Member.external_id == external_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def favorite_member_ids(db: AsyncSession, user_id: int) -> set[int]:
    stmt = select(Favorite.member_id).where(Favorite.user_id == user_id)
    return set((await db.execute(stmt)).scalars().all())
