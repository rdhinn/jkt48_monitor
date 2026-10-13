"""Normalized data transfer objects returned by connectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import AvailabilityStatus, EntryType, TicketCategory


@dataclass(slots=True)
class NormalizedMember:
    external_id: str
    name: str
    nickname: str | None = None
    team_code: str | None = None
    generation_code: str | None = None
    image_url: str | None = None
    is_active: bool = True


@dataclass(slots=True)
class NormalizedSession:
    external_line_id: str
    session_number: int | None = None
    track_number: int | None = None
    member_external_id: str | None = None
    member_name: str | None = None
    session_label: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    ticket_category: TicketCategory = TicketCategory.OTHER
    total_quota: int | None = None
    # Latest known availability (may be None when only schedule data exists)
    status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    tickets_remaining: int | None = None
    sold_count: int | None = None
    source_updated_at: datetime | None = None


@dataclass(slots=True)
class NormalizedEvent:
    external_id: str
    name: str
    entry_type: EntryType = EntryType.GENERAL
    category: TicketCategory = TicketCategory.OTHER
    category_code: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sale_valid_from: datetime | None = None
    sale_valid_to: datetime | None = None
    total_quota: int | None = None
    is_active: bool = True
    source_url: str | None = None
    sessions: list[NormalizedSession] = field(default_factory=list)


@dataclass(slots=True)
class SourceState:
    """Reported capability/health for a data source."""

    name: str
    configured: bool
    available: bool
    supported_features: list[str] = field(default_factory=list)
    message: str | None = None
    base_url: str | None = None
    docs_url: str | None = None
