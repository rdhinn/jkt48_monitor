"""Synchronization: pull from a connector and persist normalized data."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector, ConnectorError, NotConfiguredError
from app.connectors.types import NormalizedEvent, NormalizedMember
from app.core.logging import get_logger
from app.models import AvailabilitySnapshot, Event, EventSession, Member
from app.models.enums import AvailabilityStatus
from app.repositories import availability as availability_repo
from app.repositories import sources as source_repo
from app.services.diff import Change, CurrentState, PreviousState, detect_changes

logger = get_logger(__name__)

SOURCE_URL = "https://jkt48.com/"


@dataclass
class SyncResult:
    success: bool = True
    members_synced: int = 0
    events_synced: int = 0
    sessions_synced: int = 0
    snapshots_written: int = 0
    changes: list[Change] = field(default_factory=list)
    rows_by_session: dict[int, dict] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


async def _timed_check(db: AsyncSession, source: str, endpoint: str, coro):
    """Run a connector coroutine, recording a SourceCheck row."""
    started = time.perf_counter()
    try:
        result = await coro
        duration = int((time.perf_counter() - started) * 1000)
        await source_repo.record(
            db,
            source_name=source,
            endpoint_name=endpoint,
            success=True,
            response_status=200,
            duration_ms=duration,
        )
        return result, None
    except NotConfiguredError as exc:
        duration = int((time.perf_counter() - started) * 1000)
        await source_repo.record(
            db,
            source_name=source,
            endpoint_name=endpoint,
            success=False,
            error_message=str(exc),
            duration_ms=duration,
        )
        return None, exc
    except ConnectorError as exc:
        duration = int((time.perf_counter() - started) * 1000)
        await source_repo.record(
            db,
            source_name=source,
            endpoint_name=endpoint,
            success=False,
            response_status=exc.status_code,
            error_message=str(exc),
            duration_ms=duration,
        )
        return None, exc


async def _upsert_member(db: AsyncSession, data: NormalizedMember) -> Member:
    member = await _get_by_external(db, Member, data.external_id)
    if member is None:
        member = Member(external_id=data.external_id, name=data.name)
        db.add(member)
    member.name = data.name
    member.nickname = data.nickname
    member.team_code = data.team_code
    member.generation_code = data.generation_code
    member.image_url = data.image_url
    member.is_active = data.is_active
    member.source = "48pedia"
    await db.flush()
    return member


async def _get_by_external(db: AsyncSession, model, external_id: str):
    stmt = select(model).where(model.external_id == external_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def _upsert_event(db: AsyncSession, data: NormalizedEvent) -> Event:
    event = await _get_by_external(db, Event, data.external_id)
    if event is None:
        event = Event(external_id=data.external_id, name=data.name)
        db.add(event)
    event.name = data.name
    event.entry_type = data.entry_type.value
    event.category = data.category.value
    event.category_code = data.category_code
    event.starts_at = data.starts_at
    event.ends_at = data.ends_at
    event.sale_valid_from = data.sale_valid_from
    event.sale_valid_to = data.sale_valid_to
    event.total_quota = data.total_quota
    event.is_active = data.is_active
    event.source = "48pedia"
    event.source_url = data.source_url
    await db.flush()
    return event


async def _upsert_session(
    db: AsyncSession, event: Event, data, member_map: dict[str, int]
) -> EventSession:
    stmt = select(EventSession).where(
        EventSession.event_id == event.id,
        EventSession.external_line_id == data.external_line_id,
    )
    session = (await db.execute(stmt)).scalar_one_or_none()
    if session is None:
        session = EventSession(event_id=event.id)
        db.add(session)
    session.member_id = (
        member_map.get(data.member_external_id) if data.member_external_id else None
    )
    session.external_line_id = data.external_line_id
    session.session_label = data.session_label
    session.session_number = data.session_number
    session.track_number = data.track_number
    session.ticket_category = data.ticket_category.value
    session.starts_at = data.starts_at
    session.ends_at = data.ends_at
    session.total_quota = data.total_quota
    await db.flush()
    return session


def _payload_hash(*parts) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _str_status(value) -> str:
    return value.value if isinstance(value, AvailabilityStatus) else str(value)


async def _write_snapshot(
    db: AsyncSession,
    session: EventSession,
    data,
    *,
    event_name: str,
    member_name: str | None,
) -> tuple[Change, ...]:
    previous_snapshot = await availability_repo.latest_snapshot(db, session.id)
    previous = None
    if previous_snapshot is not None:
        previous = PreviousState(
            status=previous_snapshot.status,
            tickets_remaining=previous_snapshot.tickets_remaining,
            starts_at=session.starts_at,
        )
    status_value = _str_status(data.status)
    current = CurrentState(
        status=status_value,
        tickets_remaining=data.tickets_remaining,
        starts_at=data.starts_at,
    )
    changes = detect_changes(
        session.id,
        previous,
        current,
        event_key_prefix=f"ev{event_name}",
    )

    snapshot = AvailabilitySnapshot(
        session_id=session.id,
        status=status_value,
        tickets_remaining=data.tickets_remaining,
        sold_count=data.sold_count,
        total_quota=data.total_quota,
        source="48pedia",
        source_updated_at=data.source_updated_at,
        observed_at=_now(),
        raw_payload_hash=_payload_hash(session.id, status_value, data.tickets_remaining),
    )
    db.add(snapshot)
    await db.flush()
    return tuple(changes)


def _now():
    from app.db.base import utcnow

    return utcnow()


async def sync_members(db: AsyncSession, connector: BaseConnector) -> tuple[int, str | None]:
    data, error = await _timed_check(db, connector.name, "members", connector.fetch_members())
    if error is not None:
        return 0, str(error)
    count = 0
    for item in data or []:
        await _upsert_member(db, item)
        count += 1
    return count, None


async def sync_schedule_events(
    db: AsyncSession, connector: BaseConnector
) -> tuple[int, str | None]:
    data, error = await _timed_check(db, connector.name, "events", connector.fetch_events())
    if error is not None:
        return 0, str(error)
    count = 0
    for item in data or []:
        await _upsert_event(db, item)
        count += 1
    return count, None


async def sync_ticket_events(
    db: AsyncSession, connector: BaseConnector, result: SyncResult
) -> None:
    data, error = await _timed_check(
        db, connector.name, "exclusives/sales", connector.fetch_ticket_sales()
    )
    if error is not None:
        result.errors.append(str(error))
        result.success = False
        return

    member_map = await _member_id_map(db)
    for event_data in data or []:
        event = await _upsert_event(db, event_data)
        result.events_synced += 1
        for session_data in event_data.sessions:
            session = await _upsert_session(db, event, session_data, member_map)
            result.sessions_synced += 1
            member_name = session_data.member_name
            changes = await _write_snapshot(
                db,
                session,
                session_data,
                event_name=event.name,
                member_name=member_name,
            )
            result.snapshots_written += 1
            result.changes.extend(changes)
            result.rows_by_session[session.id] = {
                "session_id": session.id,
                "event_id": event.id,
                "event_name": event.name,
                "member_id": session.member_id,
                "member_name": member_name,
                "ticket_category": session_data.ticket_category.value,
                "session_number": session_data.session_number,
                "status": _str_status(session_data.status),
                "tickets_remaining": session_data.tickets_remaining,
                "source": "48pedia",
            }


async def _member_id_map(db: AsyncSession) -> dict[str, int]:
    stmt = select(Member.external_id, Member.id)
    rows = (await db.execute(stmt)).all()
    return {external: pk for external, pk in rows}


async def perform_sync(
    db: AsyncSession,
    connector: BaseConnector,
    *,
    include_schedule: bool = True,
    include_members: bool = True,
) -> SyncResult:
    result = SyncResult()
    if not connector.configured:
        await source_repo.record(
            db,
            source_name=connector.name,
            endpoint_name="members",
            success=False,
            error_message="Connector not configured (missing API key)",
        )
        result.success = False
        result.errors.append("Data source not configured. Set JKT48_API_KEY.")
        await db.commit()
        return result

    if include_members:
        count, error = await sync_members(db, connector)
        result.members_synced = count
        if error:
            result.errors.append(error)
            result.success = False
    if include_schedule:
        count, error = await sync_schedule_events(db, connector)
        result.events_synced += count
        if error:
            result.errors.append(error)

    await sync_ticket_events(db, connector, result)
    await db.commit()
    return result
