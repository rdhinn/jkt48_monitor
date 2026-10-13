"""Adapter for the 48pedia.id Public API.

Verified against https://48pedia.id/portal/docs (OpenAPI 3.1, server
``https://api.48pedia.id/v1``). Authentication is ``Authorization: Bearer <key>``.

Verified capability summary:
  * Members:  GET /members
  * Events:   GET /events, GET /shows
  * Ticket stock: GET /exclusives, /exclusives/{code},
                  /exclusives/{code}/sales, /exclusives/{code}/sales-history
The sales endpoints return numeric ``sold_count`` / ``available_count`` per
session line, which is the only source of real ticket counts used here.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timezone, timedelta

import httpx

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    NotConfiguredError,
    RateLimitedError,
)
from app.connectors.normalize import (
    compute_tickets_remaining,
    derive_status,
    normalize_category,
    normalize_entry_type,
    parse_int,
)
from app.connectors.schemas import (
    Envelope,
    ExclusiveDetail,
    ExclusiveListItem,
    EventListItem,
    MemberItem,
    PaginationMeta,
    SalesCurrent,
    ShowListItem,
)
from app.connectors.types import NormalizedEvent, NormalizedMember, NormalizedSession
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_WIB = timezone(timedelta(hours=7))


def _parse_date(value: str | None, tz: timezone) -> date | None:
    if not value:
        return None
    text = value.strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_clock(value: str | None) -> time | None:
    if not value:
        return None
    text = value.strip()
    if "T" in text:
        text = text.split("T", 1)[1]
    text = text.replace("Z", "")
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text[:8], fmt).time()
        except ValueError:
            continue
    return None


def parse_datetime(
    date_value: str | None, time_value: str | None, *, tz: timezone
) -> datetime | None:
    """Combine a date string and a clock string into an aware datetime."""
    if date_value and "T" in date_value and time_value is None:
        text = date_value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz)
        except ValueError:
            pass
    day = _parse_date(date_value, tz)
    clock = _parse_clock(time_value)
    if day is None:
        return None
    if clock is None:
        return datetime.combine(day, time(0, 0), tzinfo=tz)
    return datetime.combine(day, clock, tzinfo=tz)


class Jkt48ApiConnector(BaseConnector):
    name = "48pedia"
    docs_url = "https://48pedia.id/portal/docs"
    supported_features = [
        "members",
        "events",
        "schedules",
        "ticket_stock",
        "ticket_stock_history",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else settings.jkt48_api_key).strip()
        self.base_url = (base_url or settings.jkt48_api_base_url).rstrip("/")
        self._max_retries = settings.http_max_retries
        self._owns_client = client is None
        headers = {"Accept": "application/json", "User-Agent": "jkt48-monitor/1.0"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=settings.http_timeout_seconds,
        )
        self.last_rate_limit_wait: float = 0.0

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self.configured:
            raise NotConfiguredError(
                "JKT48_API_KEY is not configured; live data is unavailable."
            )
        attempt = 0
        delay = 0.5
        last_error: Exception | None = None
        while attempt <= self._max_retries:
            try:
                response = await self._client.request(method, path, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                attempt += 1
                if attempt > self._max_retries:
                    break
                await asyncio.sleep(delay)
                delay *= 2
                continue

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if (retry_after or "").isdigit() else delay
                wait = min(wait, 30.0)
                self.last_rate_limit_wait = wait
                attempt += 1
                if attempt > self._max_retries:
                    raise RateLimitedError(
                        "Rate limit exceeded by the data source",
                        retry_after=int(wait),
                    )
                await asyncio.sleep(wait)
                delay *= 2
                continue

            if response.status_code >= 500:
                last_error = ConnectorError(
                    f"Upstream error {response.status_code}",
                    status_code=response.status_code,
                    retryable=True,
                )
                attempt += 1
                if attempt > self._max_retries:
                    break
                await asyncio.sleep(delay)
                delay *= 2
                continue

            return response

        if isinstance(last_error, ConnectorError):
            raise last_error
        raise ConnectorError(
            f"Request to {path} failed: {last_error}", retryable=True
        )

    async def _get_json(self, path: str, params: dict | None = None) -> dict:
        response = await self._request("GET", path, params=params)
        if response.status_code == 401:
            raise ConnectorError(
                "API key rejected (401). Check JKT48_API_KEY.",
                status_code=401,
            )
        if response.status_code == 403:
            raise ConnectorError(
                "API key revoked or expired (403).", status_code=403
            )
        if response.status_code >= 400:
            raise ConnectorError(
                f"API returned {response.status_code}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - malformed upstream
            raise ConnectorError("Invalid JSON from source") from exc

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------
    async def fetch_members(self) -> list[NormalizedMember]:
        members: list[NormalizedMember] = []
        page = 1
        while True:
            payload = await self._get_json(
                "/members", {"page": page, "per_page": settings.sync_page_size}
            )
            envelope = Envelope[list[MemberItem]].model_validate(payload)
            for item in envelope.data or []:
                members.append(
                    NormalizedMember(
                        external_id=item.code,
                        name=item.name,
                        nickname=item.nickname,
                        team_code=item.team_code,
                        generation_code=item.generation_code,
                        image_url=item.photo,
                        is_active=True,
                    )
                )
            meta = PaginationMeta.model_validate(envelope.meta or {})
            if not meta.page or not meta.per_page or not meta.total:
                break
            if meta.page * meta.per_page >= meta.total:
                break
            page += 1
            if page > 50:  # hard safety bound
                break
        return members

    # ------------------------------------------------------------------
    # Schedule-level events (shows + events)
    # ------------------------------------------------------------------
    async def fetch_events(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []

        show_payload = await self._get_json(
            "/shows", {"page": 1, "per_page": settings.sync_page_size}
        )
        for item in Envelope[list[ShowListItem]].model_validate(show_payload).data or []:
            events.append(
                NormalizedEvent(
                    external_id=item.code,
                    name=item.title or item.code,
                    entry_type=normalize_entry_type("SHOW"),
                    starts_at=parse_datetime(
                        item.show_date_utc or item.show_date_wib,
                        item.start_time,
                        tz=timezone.utc,
                    ),
                    ends_at=parse_datetime(
                        item.show_date_utc or item.show_date_wib,
                        item.end_time,
                        tz=timezone.utc,
                    ),
                    is_active=bool(item.is_active),
                    source_url=f"https://jkt48.com/theater/schedule",
                )
            )

        event_payload = await self._get_json(
            "/events", {"page": 1, "per_page": settings.sync_page_size}
        )
        for item in Envelope[list[EventListItem]].model_validate(event_payload).data or []:
            events.append(
                NormalizedEvent(
                    external_id=item.code,
                    name=item.title or item.code,
                    entry_type=normalize_entry_type("EVENT"),
                    starts_at=parse_datetime(
                        item.event_date_utc or item.event_date_wib,
                        item.start_time,
                        tz=timezone.utc,
                    ),
                    ends_at=parse_datetime(
                        item.event_date_utc or item.event_date_wib,
                        item.end_time,
                        tz=timezone.utc,
                    ),
                    is_active=bool(item.is_active),
                    source_url="https://jkt48.com/news",
                )
            )
        return events

    # ------------------------------------------------------------------
    # Ticket events (exclusives) with per-session stock
    # ------------------------------------------------------------------
    async def _list_active_exclusives(self) -> list[ExclusiveListItem]:
        items: list[ExclusiveListItem] = []
        page = 1
        while True:
            payload = await self._get_json(
                "/exclusives",
                {"page": page, "per_page": settings.sync_page_size},
            )
            envelope = Envelope[list[ExclusiveListItem]].model_validate(payload)
            items.extend(envelope.data or [])
            meta = PaginationMeta.model_validate(envelope.meta or {})
            if not meta.page or not meta.per_page or not meta.total:
                break
            if meta.page * meta.per_page >= meta.total:
                break
            page += 1
            if page > 20:
                break
        return [item for item in items if item.is_active]

    async def _fetch_one_exclusive(self, code: str) -> NormalizedEvent | None:
        detail_payload = await self._get_json(f"/exclusives/{code}")
        detail = Envelope[ExclusiveDetail].model_validate(detail_payload).data
        if detail is None:
            return None

        try:
            sales_payload = await self._get_json(f"/exclusives/{code}/sales")
            sales = Envelope[SalesCurrent].model_validate(sales_payload).data
        except ConnectorError as exc:
            logger.warning("Sales unavailable for %s: %s", code, exc)
            sales = None

        category = normalize_category(detail.category_code, detail.title)
        event = NormalizedEvent(
            external_id=detail.code,
            name=detail.title or detail.code,
            entry_type=normalize_entry_type("EXCLUSIVE"),
            category=category,
            category_code=detail.category_code,
            sale_valid_from=parse_datetime(detail.sale_valid_from, None, tz=_WIB),
            sale_valid_to=parse_datetime(detail.sale_valid_to, None, tz=_WIB),
            total_quota=parse_int(detail.total_quota),
            is_active=bool(detail.is_active),
            source_url=f"https://jkt48.com/",
        )

        sales_by_key: dict[str, object] = {}
        if sales is not None:
            for line in sales.lines:
                key = (
                    f"{line.session_number}|{line.track_number}|"
                    f"{line.member_code or ''}"
                )
                sales_by_key[key] = line

        first_start: datetime | None = None
        for session in detail.sessions:
            starts_at = parse_datetime(session.session_date_utc, session.start_time, tz=_WIB)
            ends_at = parse_datetime(session.session_date_utc, session.end_time, tz=_WIB)
            if first_start is None or (starts_at and starts_at < first_start):
                first_start = starts_at
            for line in session.lines:
                key = (
                    f"{session.session_number}|{line.track_number}|"
                    f"{line.member_code or ''}"
                )
                sales_line = sales_by_key.get(key)
                available = getattr(sales_line, "available_count", None)
                sold = getattr(sales_line, "sold_count", None)
                remaining = compute_tickets_remaining(
                    parse_int(available), parse_int(sold), event.total_quota
                )
                if sales is None:
                    status = derive_status(
                        tickets_remaining=None, sales_open=None
                    )
                else:
                    status = derive_status(
                        tickets_remaining=remaining,
                        sales_open=bool(getattr(sales, "sales_open", None)),
                    )
                event.sessions.append(
                    NormalizedSession(
                        external_line_id=key,
                        session_number=session.session_number,
                        track_number=line.track_number,
                        member_external_id=line.member_code,
                        member_name=line.member_name,
                        session_label=(
                            f"Sesi {session.session_number}"
                            if session.session_number is not None
                            else None
                        ),
                        starts_at=starts_at,
                        ends_at=ends_at,
                        ticket_category=category,
                        total_quota=event.total_quota,
                        status=status,
                        tickets_remaining=remaining,
                        sold_count=parse_int(sold),
                        source_updated_at=getattr(sales, "as_of", None),
                    )
                )
        event.starts_at = first_start
        return event

    async def fetch_ticket_sales(self) -> list[NormalizedEvent]:
        exclusives = await self._list_active_exclusives()
        results: list[NormalizedEvent] = []
        for item in exclusives:
            try:
                event = await self._fetch_one_exclusive(item.code)
            except ConnectorError as exc:
                # One broken exclusive must not abort the whole sync.
                logger.warning("Skipping exclusive %s: %s", item.code, exc)
                continue
            if event is not None:
                results.append(event)
        return results

    async def fetch_event_sales(self, external_id: str) -> NormalizedEvent | None:
        return await self._fetch_one_exclusive(external_id)

    async def health(self) -> bool:
        if not self.configured:
            return False
        try:
            await self._get_json("/check-key")
            return True
        except ConnectorError:
            return False
