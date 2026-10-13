"""Pydantic models mirroring the 48pedia.id Public API responses.

Docs: https://48pedia.id/portal/docs  (server: https://api.48pedia.id/v1)
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PaginationMeta(_Base):
    as_of: datetime | None = None
    page: int | None = None
    per_page: int | None = None
    total: int | None = None


class AsOfMeta(_Base):
    as_of: datetime | None = None


class Envelope(_Base, Generic[T]):
    code: int
    message: str
    data: T
    meta: dict | None = None


class MemberItem(_Base):
    code: str
    name: str
    nickname: str | None = None
    team_code: str | None = None
    generation_code: str | None = None
    photo: str | None = None


class ExclusiveListItem(_Base):
    code: str
    category_code: str | None = None
    title: str | None = None
    base_price: float | None = None
    total_quota: int | None = None
    is_active: bool = True
    sale_valid_from: str | None = None
    sale_valid_to: str | None = None


class ExclusiveSessionLine(_Base):
    track_number: int | None = None
    member_code: str | None = None
    member_name: str | None = None


class ExclusiveSession(_Base):
    session_number: int | None = None
    session_date_utc: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    reception_start: str | None = None
    reception_end: str | None = None
    prep_start: str | None = None
    prep_end: str | None = None
    lines: list[ExclusiveSessionLine] = Field(default_factory=list)


class ExclusiveDetail(_Base):
    entry_type: str | None = None
    code: str
    category_code: str | None = None
    title: str | None = None
    total_quota: int | None = None
    is_active: bool = True
    sale_valid_from: str | None = None
    sale_valid_to: str | None = None
    sessions: list[ExclusiveSession] = Field(default_factory=list)


class SalesLine(_Base):
    session_line_id: int | None = None
    session_number: int | None = None
    track_number: int | None = None
    member_code: str | None = None
    member_name: str | None = None
    sold_count: int | None = None
    available_count: int | None = None
    captured_at: datetime | None = None


class SalesCurrent(_Base):
    code: str
    sales_open: bool | None = None
    as_of: datetime | None = None
    fill_rate: float | None = None
    lines: list[SalesLine] = Field(default_factory=list)


class EventListItem(_Base):
    code: str
    title: str | None = None
    event_date_utc: str | None = None
    event_date_wib: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    team_code: str | None = None
    is_in_theater: bool = False
    is_active: bool = True


class ShowListItem(_Base):
    code: str
    title: str | None = None
    show_date_utc: str | None = None
    show_date_wib: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    setlist_code: str | None = None
    team_code: str | None = None
    is_birthday: bool = False
    is_active: bool = True


class ErrorBody(_Base):
    code: int | None = None
    errorCode: int | None = None
    message: str | None = None
