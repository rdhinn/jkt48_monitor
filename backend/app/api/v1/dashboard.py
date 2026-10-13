"""Dashboard summary endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.connectors.registry import get_connector, source_states
from app.models import Event, EventSession, Member
from app.repositories import availability as availability_repo
from app.repositories import sources as source_repo
from app.schemas.dashboard import (
    DashboardOut,
    DashboardStats,
    SourceStatusOut,
)
from app.schemas.event import ChangeOut
from app.services.diff import CurrentState, PreviousState, detect_changes

router = APIRouter(tags=["dashboard"])


def _recent_changes(rows: list[dict], limit: int = 20) -> list[ChangeOut]:
    # rows newest-first, group by session
    latest: dict[int, dict] = {}
    seen_sessions: set[int] = set()
    changes: list[ChangeOut] = []
    for row in rows:
        sid = row["session_id"]
        if sid not in latest:
            latest[sid] = row
            continue
        if sid in seen_sessions:
            continue
        seen_sessions.add(sid)
        prev = latest[sid]
        detected = detect_changes(
            sid,
            PreviousState(
                status=row["status"], tickets_remaining=row["tickets_remaining"]
            ),
            CurrentState(
                status=prev["status"], tickets_remaining=prev["tickets_remaining"]
            ),
            event_key_prefix="dash",
        )
        for change in detected:
            changes.append(
                ChangeOut(
                    session_id=sid,
                    event_name=row["event_name"],
                    member_name=row.get("member_name"),
                    ticket_category=row["ticket_category"],
                    field=change.field,
                    previous=change.previous,
                    current=change.current,
                    observed_at=prev["observed_at"],
                    source=prev["source"],
                )
            )
    changes.sort(key=lambda c: c.observed_at, reverse=True)
    return changes[:limit]


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: DbSession) -> DashboardOut:
    total_members = (
        await db.execute(select(func.count()).select_from(Member))
    ).scalar_one()
    active_members = (
        await db.execute(
            select(func.count()).select_from(Member).where(Member.is_active.is_(True))
        )
    ).scalar_one()
    total_events = (
        await db.execute(select(func.count()).select_from(Event))
    ).scalar_one()
    active_events = (
        await db.execute(
            select(func.count()).select_from(Event).where(Event.is_active.is_(True))
        )
    ).scalar_one()
    total_sessions = (
        await db.execute(select(func.count()).select_from(EventSession))
    ).scalar_one()

    counts = await availability_repo.status_counts(db)
    category_counts = await availability_repo.category_counts(db)
    declining = await availability_repo.declining_sessions(db)

    changes_rows = await availability_repo.recent_change_rows(db)
    recent_changes = _recent_changes(changes_rows)

    latest_snapshot_at = (
        await db.execute(select(func.max(availability_repo.AvailabilitySnapshot.observed_at)))
    ).scalar_one()

    connector = get_connector()
    latest_checks = await source_repo.latest_by_source(db)
    latest_success = await source_repo.latest_success_by_source(db)
    states = source_states(connector)
    sources = [
        SourceStatusOut(
            name=state.name,
            configured=state.configured,
            available=state.available,
            supported_features=state.supported_features,
            message=state.message,
            base_url=state.base_url,
            docs_url=state.docs_url,
            last_checked_at=(
                latest_checks[state.name].checked_at if state.name in latest_checks else None
            ),
            last_success_at=(
                latest_success[state.name].checked_at
                if state.name in latest_success
                else None
            ),
            last_error=(
                latest_checks[state.name].error_message
                if state.name in latest_checks
                and not latest_checks[state.name].success
                else None
            ),
        )
        for state in states
    ]

    data_available = bool(counts)
    notes: list[str] = []
    if not connector.configured:
        notes.append(
            "Sumber data 48pedia belum dikonfigurasi (JKT48_API_KEY kosong). "
            "Data ketersediaan belum tersedia."
        )
    if not data_available:
        notes.append("Belum ada snapshot ketersediaan yang tersimpan.")

    stats = DashboardStats(
        total_members=int(total_members),
        active_members=int(active_members),
        total_events=int(total_events),
        active_events=int(active_events),
        total_sessions=int(total_sessions),
        available_sessions=counts.get("available", 0),
        sold_out_sessions=counts.get("sold_out", 0),
        not_open_sessions=counts.get("not_open", 0),
        unknown_sessions=counts.get("unknown", 0),
        unavailable_sessions=counts.get("unavailable", 0),
        sessions_with_declining_stock=declining,
        data_available=data_available,
        last_observed_at=latest_snapshot_at,
        last_check_at=(
            max((c.checked_at for c in latest_checks.values()), default=None)
            if latest_checks
            else None
        ),
        api_connected=connector.configured and bool(latest_success),
        notes=notes,
    )

    return DashboardOut(
        stats=stats,
        recent_changes=recent_changes,
        availability_by_category=category_counts,
        sources=sources,
    )
