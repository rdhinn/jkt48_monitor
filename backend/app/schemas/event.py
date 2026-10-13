"""Event and availability schemas."""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class SessionOut(ORMModel):
    id: int
    session_label: str | None = None
    session_number: int | None = None
    track_number: int | None = None
    ticket_category: str
    member_id: int | None = None
    member_name: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    total_quota: int | None = None


class EventOut(ORMModel):
    id: int
    external_id: str
    name: str
    entry_type: str
    category: str
    category_code: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sale_valid_from: datetime | None = None
    sale_valid_to: datetime | None = None
    total_quota: int | None = None
    is_active: bool
    source: str
    source_url: str | None = None
    sessions: list[SessionOut] = []


class AvailabilityRow(ORMModel):
    session_id: int
    event_id: int
    event_external_id: str
    event_name: str
    entry_type: str
    ticket_category: str
    session_label: str | None = None
    session_number: int | None = None
    starts_at: datetime | None = None
    member_id: int | None = None
    member_name: str | None = None
    status: str
    tickets_remaining: int | None = None
    total_quota: int | None = None
    source: str
    source_url: str | None = None
    observed_at: datetime | None = None
    source_updated_at: datetime | None = None


class HistoryPoint(ORMModel):
    observed_at: datetime
    status: str
    tickets_remaining: int | None = None
    sold_count: int | None = None
    source: str
    session_id: int
    member_name: str | None = None
    event_name: str


class ChangeOut(ORMModel):
    session_id: int
    event_name: str
    member_name: str | None = None
    ticket_category: str
    field: str
    previous: str | None = None
    current: str | None = None
    observed_at: datetime
    source: str
