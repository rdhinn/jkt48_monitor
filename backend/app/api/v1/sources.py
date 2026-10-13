"""Health and source-status endpoints."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from app.api.deps import DbSession
from app.connectors.registry import get_connector, source_states
from app.repositories import sources as source_repo

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: DbSession) -> dict:
    connector = get_connector()
    return {
        "status": "ok",
        "source_configured": connector.configured,
        "source": connector.name,
    }


@router.get("/sources/status")
async def sources_status(db: DbSession) -> dict:
    connector = get_connector()
    available = None
    message = None
    if connector.configured:
        try:
            available = await connector.health()
        except Exception as exc:  # noqa: BLE001
            available = False
            message = str(exc)
    states = source_states(connector, available=available, message=message)

    latest = await source_repo.latest_by_source(db)
    latest_success = await source_repo.latest_success_by_source(db)

    result = []
    for state in states:
        check = latest.get(state.name)
        success = latest_success.get(state.name)
        result.append(
            {
                **asdict(state),
                "last_checked_at": check.checked_at if check else None,
                "last_success_at": success.checked_at if success else None,
                "last_error": (
                    check.error_message if check and not check.success else None
                ),
            }
        )
    return {"sources": result}
