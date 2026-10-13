"""Manual monitoring trigger and worker status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import MonitorRefreshResult
from app.services.monitor import (
    ManualRefreshRateLimited,
    MonitorBusyError,
    monitor,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/refresh", response_model=MonitorRefreshResult)
async def refresh(db: DbSession, user: CurrentUser) -> MonitorRefreshResult:
    """Trigger a one-off sync. Protected and rate limited to avoid abuse."""
    try:
        result = await monitor.run_once(db, manual=True)
    except ManualRefreshRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except MonitorBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    notifications_sent = int(result.rows_by_session.pop("__notifications_sent__", 0) or 0)
    return MonitorRefreshResult(
        started=True,
        message="Pemeriksaan manual selesai.",
        members_synced=result.members_synced,
        events_synced=result.events_synced,
        sessions_synced=result.sessions_synced,
        changes_detected=len(result.changes),
        notifications_sent=notifications_sent,
        errors=result.errors,
    )


@router.get("/status")
async def monitor_status() -> dict:
    return monitor.status()
