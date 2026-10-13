"""Change detection between availability snapshots.

Pure functions: no database or network access, so they are trivially testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.enums import AvailabilityStatus


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

# Transitions we always care about, per the monitoring spec.
_SIGNIFICANT_STATUS_TRANSITIONS = {
    (AvailabilityStatus.UNKNOWN.value, AvailabilityStatus.AVAILABLE.value),
    (AvailabilityStatus.SOLD_OUT.value, AvailabilityStatus.AVAILABLE.value),
    (AvailabilityStatus.AVAILABLE.value, AvailabilityStatus.SOLD_OUT.value),
}


@dataclass(slots=True)
class PreviousState:
    status: str | None
    tickets_remaining: int | None
    starts_at: datetime | None = None


@dataclass(slots=True)
class CurrentState:
    status: str
    tickets_remaining: int | None
    starts_at: datetime | None = None


@dataclass(slots=True)
class Change:
    session_id: int
    field: str
    previous: str | None
    current: str | None
    significant: bool
    event_key: str


def _fmt(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def detect_changes(
    session_id: int,
    previous: PreviousState | None,
    current: CurrentState,
    *,
    event_key_prefix: str,
    schedule_tolerance_seconds: int = 60,
) -> list[Change]:
    """Return the list of changes between ``previous`` and ``current``.

    ``previous is None`` means this is a brand new session.
    """
    changes: list[Change] = []

    if previous is None or previous.status is None:
        # New event/session. Only notify when there is real availability data.
        changes.append(
            Change(
                session_id=session_id,
                field="new_event",
                previous=None,
                current=current.status,
                significant=current.status
                in (AvailabilityStatus.AVAILABLE.value, AvailabilityStatus.SOLD_OUT.value),
                event_key=f"{event_key_prefix}:new:{session_id}",
            )
        )
        return changes

    if previous.status != current.status:
        transition = (previous.status, current.status)
        changes.append(
            Change(
                session_id=session_id,
                field="status",
                previous=previous.status,
                current=current.status,
                significant=transition in _SIGNIFICANT_STATUS_TRANSITIONS,
                event_key=(
                    f"{event_key_prefix}:status:{session_id}:"
                    f"{previous.status}->{current.status}"
                ),
            )
        )

    if previous.tickets_remaining != current.tickets_remaining:
        changes.append(
            Change(
                session_id=session_id,
                field="tickets_remaining",
                previous=_fmt(previous.tickets_remaining),
                current=_fmt(current.tickets_remaining),
                significant=(
                    previous.tickets_remaining is not None
                    and current.tickets_remaining is not None
                ),
                event_key=(
                    f"{event_key_prefix}:tickets:{session_id}:"
                    f"{previous.tickets_remaining}->{current.tickets_remaining}"
                ),
            )
        )

    prev_start = _aware(previous.starts_at)
    curr_start = _aware(current.starts_at)
    if (
        prev_start is not None
        and curr_start is not None
        and abs((curr_start - prev_start).total_seconds()) > schedule_tolerance_seconds
    ):
        changes.append(
            Change(
                session_id=session_id,
                field="schedule",
                previous=previous.starts_at.isoformat(),
                current=current.starts_at.isoformat(),
                significant=True,
                event_key=(
                    f"{event_key_prefix}:schedule:{session_id}:"
                    f"{previous.starts_at.isoformat()}->{current.starts_at.isoformat()}"
                ),
            )
        )

    return changes
