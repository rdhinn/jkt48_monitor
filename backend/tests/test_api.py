"""End-to-end API tests using a real (in-memory) database."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models import (
    AvailabilitySnapshot,
    AvailabilityStatus,
    Event,
    EventSession,
    Member,
    TicketCategory,
)
from app.repositories import favorites as fav_repo


async def seed_data(db_session):
    member = Member(
        external_id="FIONY",
        name="Fiony Alveria",
        nickname="Fiony",
        team_code="K3",
        generation_code="GEN-8",
        image_url="https://example.com/fiony.jpg",
        is_active=True,
        source="48pedia",
    )
    db_session.add(member)
    event = Event(
        external_id="EX1",
        name="Video Call Event",
        entry_type="EXCLUSIVE",
        category=TicketCategory.VIDEO_CALL.value,
        category_code="VC",
        starts_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
        is_active=True,
        source="48pedia",
    )
    db_session.add(event)
    await db_session.flush()
    session = EventSession(
        event_id=event.id,
        member_id=member.id,
        external_line_id="line1",
        session_label="Sesi 1",
        session_number=1,
        track_number=1,
        ticket_category=TicketCategory.VIDEO_CALL.value,
        starts_at=datetime(2025, 7, 2, 12, tzinfo=timezone.utc),
        total_quota=10,
    )
    db_session.add(session)
    await db_session.flush()
    snap = AvailabilitySnapshot(
        session_id=session.id,
        status=AvailabilityStatus.AVAILABLE.value,
        tickets_remaining=7,
        sold_count=3,
        total_quota=10,
        source="48pedia",
        source_updated_at=datetime(2025, 7, 2, 10, tzinfo=timezone.utc),
        observed_at=datetime(2025, 7, 2, 10, tzinfo=timezone.utc),
    )
    db_session.add(snap)
    await db_session.commit()
    return {"member": member, "event": event, "session": session}


class TestApi:
    async def test_health(self, client):
        r = await client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_members_list(self, client, db_session):
        await seed_data(db_session)
        r = await client.get("/api/v1/members")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Fiony Alveria"

    async def test_members_search_and_favorite_filter(self, client, db_session):
        data = await seed_data(db_session)
        r = await client.get("/api/v1/members", params={"q": "fion"})
        assert r.json()["total"] == 1
        r = await client.get("/api/v1/members", params={"q": "zzz"})
        assert r.json()["total"] == 0

        # favorite then filter favorites_only
        await fav_repo.add(db_session, user_id=1, member_id=data["member"].id)
        await db_session.commit()
        r = await client.get("/api/v1/members", params={"favorites_only": "true"})
        assert r.json()["total"] == 1

    async def test_members_status_filter(self, client, db_session):
        await seed_data(db_session)
        r = await client.get("/api/v1/members", params={"status": "available"})
        assert r.json()["total"] == 1
        r = await client.get("/api/v1/members", params={"status": "sold_out"})
        assert r.json()["total"] == 0

    async def test_availability_filters(self, client, db_session):
        await seed_data(db_session)
        r = await client.get("/api/v1/availability")
        assert r.status_code == 200
        rows = r.json()["items"]
        assert len(rows) == 1
        assert rows[0]["tickets_remaining"] == 7
        assert rows[0]["member_name"] == "Fiony Alveria"

        r = await client.get("/api/v1/availability", params={"category": "video_call"})
        assert r.json()["total"] == 1
        r = await client.get("/api/v1/availability", params={"category": "meet_greet"})
        assert r.json()["total"] == 0
        r = await client.get("/api/v1/availability", params={"status": "sold_out"})
        assert r.json()["total"] == 0
        r = await client.get("/api/v1/availability", params={"status": "available"})
        assert r.json()["total"] == 1

    async def test_availability_history(self, client, db_session):
        await seed_data(db_session)
        r = await client.get("/api/v1/availability/history")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    async def test_events(self, client, db_session):
        data = await seed_data(db_session)
        r = await client.get("/api/v1/events")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        r = await client.get(f"/api/v1/events/{data['event'].id}")
        assert r.status_code == 200
        assert r.json()["external_id"] == "EX1"

    async def test_dashboard_shows_real_data(self, client, db_session):
        await seed_data(db_session)
        r = await client.get("/api/v1/dashboard")
        assert r.status_code == 200
        stats = r.json()["stats"]
        assert stats["data_available"] is True
        assert stats["total_members"] == 1
        assert stats["total_sessions"] == 1
        assert stats["available_sessions"] == 1
        # no fake "sessions_with_declining_stock" without history of decline
        assert stats["sessions_with_declining_stock"] == 0

    async def test_favorites_flow(self, client, db_session):
        data = await seed_data(db_session)
        mid = data["member"].id
        r = await client.post(f"/api/v1/favorites/{mid}")
        assert r.status_code == 200
        assert r.json()["is_favorite"] is True
        r = await client.get("/api/v1/favorites")
        assert len(r.json()) == 1
        r = await client.delete(f"/api/v1/favorites/{mid}")
        assert r.status_code == 200
        r = await client.get("/api/v1/favorites")
        assert r.json() == []

    async def test_favorite_missing_member_404(self, client):
        r = await client.post("/api/v1/favorites/9999")
        assert r.status_code == 404

    async def test_notifications_crud(self, client):
        r = await client.put(
            "/api/v1/notifications",
            json={
                "telegram_chat_id": "1234",
                "event_type": "all",
                "member_id": None,
                "enabled": True,
            },
        )
        assert r.status_code == 200
        r = await client.get("/api/v1/notifications")
        body = r.json()
        assert len(body["subscriptions"]) == 1

    async def test_auth_token(self, client):
        r = await client.post(
            "/api/v1/auth/token", json={"username": "admin", "password": "admin"}
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_auth_bad_password(self, client):
        r = await client.post(
            "/api/v1/auth/token", json={"username": "admin", "password": "wrong"}
        )
        assert r.status_code == 401

    async def test_monitor_refresh_requires_auth(self, client):
        r = await client.post("/api/v1/monitor/refresh")
        assert r.status_code == 401

    async def test_sources_status(self, client):
        r = await client.get("/api/v1/sources/status")
        assert r.status_code == 200
        sources = r.json()["sources"]
        names = {s["name"] for s in sources}
        assert "48pedia" in names
        assert "jkt48_official" in names


class TestRateLimit:
    async def test_manual_refresh_rate_limit(self, reset_monitor):
        from app.core.config import settings
        from app.services.monitor import ManualRefreshRateLimited, monitor

        limit = settings.max_manual_refresh_per_minute
        for _ in range(limit):
            monitor._check_manual_limit()
        with pytest.raises(ManualRefreshRateLimited):
            monitor._check_manual_limit()