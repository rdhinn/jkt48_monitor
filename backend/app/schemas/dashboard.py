"""Dashboard, source, notification and auth schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.event import ChangeOut


class DashboardStats(ORMModel):
    total_members: int
    active_members: int
    total_events: int
    active_events: int
    total_sessions: int
    available_sessions: int
    sold_out_sessions: int
    not_open_sessions: int
    unknown_sessions: int
    unavailable_sessions: int
    sessions_with_declining_stock: int
    data_available: bool
    last_observed_at: datetime | None = None
    last_check_at: datetime | None = None
    api_connected: bool
    notes: list[str] = []


class DashboardOut(BaseModel):
    stats: DashboardStats
    recent_changes: list[ChangeOut]
    availability_by_category: dict[str, int]
    sources: list["SourceStatusOut"]


class SourceStatusOut(BaseModel):
    name: str
    configured: bool
    available: bool
    supported_features: list[str] = []
    message: str | None = None
    base_url: str | None = None
    docs_url: str | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class SourceCheckOut(ORMModel):
    id: int
    source_name: str
    endpoint_name: str
    success: bool
    response_status: int | None = None
    error_message: str | None = None
    checked_at: datetime
    duration_ms: int | None = None


class NotificationSubscriptionOut(ORMModel):
    id: int
    telegram_chat_id: str | None = None
    event_type: str
    member_id: int | None = None
    enabled: bool
    created_at: datetime


class NotificationSubscriptionIn(BaseModel):
    telegram_chat_id: str | None = None
    event_type: str = "all"
    member_id: int | None = None
    enabled: bool = True


class NotificationLogOut(ORMModel):
    id: int
    subscription_id: int | None = None
    event_key: str
    message: str
    delivery_status: str
    attempt_count: int
    error_message: str | None = None
    attempted_at: datetime
    delivered_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


class MonitorRefreshResult(BaseModel):
    started: bool
    message: str
    members_synced: int = 0
    events_synced: int = 0
    sessions_synced: int = 0
    changes_detected: int = 0
    notifications_sent: int = 0
    errors: list[str] = []


DashboardOut.model_rebuild()
