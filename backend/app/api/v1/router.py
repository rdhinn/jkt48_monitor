"""Aggregate /api/v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    availability,
    dashboard,
    events,
    favorites,
    members,
    monitor,
    notifications,
    sources,
)

api_router = APIRouter()
api_router.include_router(sources.router)
api_router.include_router(dashboard.router)
api_router.include_router(members.router)
api_router.include_router(events.router)
api_router.include_router(availability.router)
api_router.include_router(favorites.router)
api_router.include_router(notifications.router)
api_router.include_router(monitor.router)
api_router.include_router(auth.router)
