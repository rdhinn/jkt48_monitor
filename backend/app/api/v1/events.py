"""Event endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.repositories import events as event_repo
from app.schemas.common import Page
from app.schemas.event import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=Page[EventOut])
async def list_events(
    db: DbSession,
    q: str | None = None,
    entry_type: str | None = Query(None, description="SHOW|EVENT|EXCLUSIVE|BIRTHDAY|GENERAL"),
    category: str | None = None,
    active_only: bool = False,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> Page[EventOut]:
    events, total = await event_repo.list_events(
        db,
        q=q,
        entry_type=entry_type,
        category=category,
        active_only=active_only,
        date_from=date_from,
        date_to=date_to,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    items = [EventOut.model_validate(e) for e in events]
    return Page[EventOut](items=items, total=total, page=page, per_page=per_page)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: int, db: DbSession) -> EventOut:
    event = await event_repo.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan.")
    return EventOut.model_validate(event)
