"""Availability endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, ResolvedUser
from app.repositories import availability as availability_repo
from app.repositories import favorites as fav_repo
from app.schemas.common import Page
from app.schemas.event import AvailabilityRow, HistoryPoint

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/history", response_model=Page[HistoryPoint])
async def availability_history(
    db: DbSession,
    session_id: int | None = None,
    category: str | None = None,
    member_id: int | None = None,
    source: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=1000),
) -> Page[HistoryPoint]:
    rows, total = await availability_repo.history(
        db,
        session_id=session_id,
        category=category,
        member_id=member_id,
        source=source,
        date_from=date_from,
        date_to=date_to,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return Page[HistoryPoint](
        items=[HistoryPoint(**row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("", response_model=Page[AvailabilityRow])
async def list_availability(
    db: DbSession,
    user: ResolvedUser,
    category: str | None = Query(None, description="video_call | meet_greet | two_shot"),
    status: str | None = None,
    entry_type: str | None = None,
    member: str | None = Query(None, description="Member name search"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    event_id: int | None = None,
    member_id: int | None = None,
    favorites_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> Page[AvailabilityRow]:
    fav_ids = await fav_repo.member_ids(db, user.id)
    rows, total = await availability_repo.list_availability(
        db,
        category=category,
        status=status,
        entry_type=entry_type,
        member_q=member,
        date_from=date_from,
        date_to=date_to,
        event_id=event_id,
        member_id=member_id,
        favorite_ids=fav_ids,
        only_favorites=favorites_only,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return Page[AvailabilityRow](
        items=[AvailabilityRow(**row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{session_id}", response_model=AvailabilityRow)
async def get_availability(session_id: int, db: DbSession) -> AvailabilityRow:
    row = await availability_repo.get_availability_row(db, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    return AvailabilityRow(**row)
