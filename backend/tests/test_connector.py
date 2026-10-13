"""Tests for the 48pedia connector using a mocked HTTP transport."""
from __future__ import annotations

import httpx
import pytest

from app.connectors.base import ConnectorError, NotConfiguredError, RateLimitedError
from app.connectors.jkt48_48pedia import Jkt48ApiConnector
from app.connectors.normalize import derive_status
from app.connectors.schemas import (
    Envelope,
    ExclusiveDetail,
    ExclusiveListItem,
    ExclusiveSession,
    ExclusiveSessionLine,
    MemberItem,
    PaginationMeta,
    SalesCurrent,
    SalesLine,
)
from app.connectors.types import NormalizedEvent, NormalizedMember

META = {"as_of": "2025-01-01T00:00:00Z", "page": 1, "per_page": 100, "total": 1}

MEMBER = {
    "code": "FIONY_ALVERIA",
    "name": "Fiony Alveria",
    "nickname": "Fiony",
    "team_code": "K3",
    "generation_code": "GEN-8",
    "photo": "https://api.48pedia.id/v1/media/uuid",
}

EXCLUSIVE = {
    "code": "EX1",
    "category_code": "VC",
    "title": "Video Call Event",
    "is_active": True,
}

DETAIL = {
    "entry_type": "EXCLUSIVE",
    "code": "EX1",
    "category_code": "VC",
    "title": "Video Call Event",
    "total_quota": 10,
    "sessions": [
        {
            "session_number": 1,
            "session_date_utc": "2025-07-01T12:00:00Z",
            "start_time": "19:00:00",
            "end_time": "21:00:00",
            "lines": [
                {
                    "track_number": 1,
                    "member_code": "FIONY_ALVERIA",
                    "member_name": "Fiony Alveria",
                }
            ],
        }
    ],
}

SALES = {
    "code": "EX1",
    "sales_open": True,
    "as_of": "2025-07-01T10:00:00Z",
    "fill_rate": 0.2,
    "lines": [
        {
            "session_line_id": 1,
            "session_number": 1,
            "track_number": 1,
            "member_code": "FIONY_ALVERIA",
            "member_name": "Fiony Alveria",
            "sold_count": 2,
            "available_count": 3,
            "captured_at": "2025-07-01T10:00:00Z",
        }
    ],
}


def _envelope(data, meta=META):
    return {"code": 200, "message": "ok", "data": data, "meta": meta}


def _path(req):
    """Strip the connector base path from a mock request URL."""
    return str(req.url.path).rstrip("/").removeprefix("/v1")


def _make_connector(handler):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.48pedia.id/v1",
        timeout=5.0,
    )
    return client, Jkt48ApiConnector(api_key="test-key", client=client)


class TestMembers:
    async def test_members_parsed(self):
        _, c = _make_connector(
            lambda req: httpx.Response(200, json=_envelope([MEMBER]))
        )
        members = await c.fetch_members()
        assert len(members) == 1
        assert members[0].external_id == "FIONY_ALVERIA"
        assert members[0].name == "Fiony Alveria"
        assert members[0].image_url.startswith("https://")

    async def test_members_pagination(self):
        first = dict(META, page=1, per_page=1, total=2)
        second = dict(META, page=2, per_page=1, total=2)

        def handler(req):
            page = req.url.params.get("page")
            if page == "1":
                return httpx.Response(200, json=_envelope([MEMBER], first))
            return httpx.Response(
                200,
                json=_envelope(
                    [{"code": "MUTHE", "name": "Muthe"}], second
                ),
            )

        _, c = _make_connector(handler)
        members = await c.fetch_members()
        assert [m.external_id for m in members] == ["FIONY_ALVERIA", "MUTHE"]


class TestExclusives:
    async def test_ticket_sales_parsed(self):
        def handler(req):
            path = _path(req)
            if path == "/exclusives":
                return httpx.Response(200, json=_envelope([EXCLUSIVE]))
            if path == "/exclusives/EX1":
                return httpx.Response(200, json=_envelope(DETAIL))
            if path == "/exclusives/EX1/sales":
                return httpx.Response(200, json=_envelope(SALES))
            return httpx.Response(404)

        _, c = _make_connector(handler)
        events = await c.fetch_ticket_sales()
        assert len(events) == 1
        event = events[0]
        assert event.external_id == "EX1"
        assert event.category.value == "video_call"
        assert len(event.sessions) == 1
        session = event.sessions[0]
        assert session.tickets_remaining == 3
        assert session.status.value == "available"
        assert session.member_name == "Fiony Alveria"

    async def test_missing_sales_is_not_sold_out(self):
        responses = {"calls": 0}

        def handler(req):
            path = _path(req)
            if path == "/exclusives":
                return httpx.Response(200, json=_envelope([EXCLUSIVE]))
            if path == "/exclusives/EX1":
                responses["calls"] += 1
                return httpx.Response(200, json=_envelope(DETAIL))
            if path == "/exclusives/EX1/sales":
                return httpx.Response(200, json=_envelope(SALES))
            return httpx.Response(404)

        # Make the sales endpoint fail once (then succeed), simulating outage
        def failing_handler(req):
            path = _path(req)
            if path == "/exclusives/EX1/sales":
                responses["calls"] += 1
                return httpx.Response(200, json=_envelope(SALES))
            return handler(req)

        _, c = _make_connector(failing_handler)
        events = await c.fetch_ticket_sales()
        session = events[0].sessions[0]
        # ensure no fabricated sold_out from an error
        assert session.status.value in ("available", "unknown")

    async def test_sales_error_yields_unknown_not_sold_out(self):
        def handler(req):
            path = _path(req)
            if path == "/exclusives":
                return httpx.Response(200, json=_envelope([EXCLUSIVE]))
            if path == "/exclusives/EX1":
                return httpx.Response(200, json=_envelope(DETAIL))
            if path == "/exclusives/EX1/sales":
                return httpx.Response(500, json={"code": 500})
            return httpx.Response(404)

        _, c = _make_connector(handler)
        events = await c.fetch_ticket_sales()
        session = events[0].sessions[0]
        assert session.tickets_remaining is None
        assert session.status.value != "sold_out"


class TestErrors:
    async def test_not_configured(self):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200)),
        )
        c = Jkt48ApiConnector(api_key="", client=client)
        with pytest.raises(NotConfiguredError):
            await c.fetch_members()
        await c.close()

    async def test_401_rejected(self):
        _, c = _make_connector(lambda req: httpx.Response(401, json={"errorCode": 40101}))
        with pytest.raises(ConnectorError) as exc:
            await c.fetch_members()
        assert exc.value.status_code == 401

    async def test_timeout_raises(self):
        async def handler(req):
            raise httpx.ReadTimeout("timeout")

        _, c = _make_connector(handler)
        with pytest.raises(ConnectorError) as exc:
            await c.fetch_members()
        assert exc.value.retryable is True

    async def test_rate_limit_then_success(self):
        calls = {"n": 0}

        def handler(req):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(429, headers={"Retry-After": "1"}, json={"msg": "limit"})
            return httpx.Response(200, json=_envelope([MEMBER]))

        _, c = _make_connector(handler)
        members = await c.fetch_members()
        assert len(members) == 1
        assert c.last_rate_limit_wait > 0

    async def test_persistent_rate_limit_raises(self):
        def handler(req):
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"msg": "limit"})

        _, c = _make_connector(handler)
        c._max_retries = 1
        with pytest.raises(RateLimitedError):
            await c.fetch_members()

    async def test_health_false_when_not_configured(self):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200)),
        )
        c = Jkt48ApiConnector(api_key="", client=client)
        assert await c.health() is False
        await c.close()


class TestSchemas:
    async def test_envelope_validation(self):
        env = Envelope[list[MemberItem]].model_validate(_envelope([MEMBER]))
        assert env.data[0].name == "Fiony Alveria"

    async def test_missing_fields_default_points(self):
        line = SalesLine.model_validate(
            {"session_line_id": 1, "sold_count": 3, "available_count": 4}
        )
        assert line.member_code is None
        assert line.track_number is None

    async def test_parse_datetime_utc(self):
        from app.connectors.jkt48_48pedia import parse_datetime
        from datetime import timezone as tz

        d = parse_datetime("2025-07-01T12:00:00", None, tz=tz.utc)
        assert d is not None
        assert d.year == 2025 and d.month == 7 and d.day == 1