"""Connector registry and documented source capabilities."""
from __future__ import annotations

from app.connectors.base import BaseConnector
from app.connectors.jkt48_48pedia import Jkt48ApiConnector
from app.connectors.types import SourceState
from app.core.config import settings

_connector: Jkt48ApiConnector | None = None


def get_connector() -> Jkt48ApiConnector:
    global _connector
    if _connector is None:
        _connector = Jkt48ApiConnector()
    return _connector


def reset_connector() -> None:
    global _connector
    _connector = None


def documented_sources() -> list[dict]:
    """Static, honest description of every source we considered."""
    return [
        {
            "name": "48pedia",
            "label": "48pedia.id Public API",
            "base_url": settings.jkt48_api_base_url,
            "docs_url": "https://48pedia.id/portal/docs",
            "auth": "Bearer API key (JKT48_API_KEY)",
            "capabilities": {
                "members": "supported",
                "events": "supported",
                "schedules": "supported",
                "ticket_stock": "supported (/exclusives/{code}/sales)",
                "ticket_stock_history": "supported (/exclusives/{code}/sales-history)",
            },
            "notes": "Requires a free API key. This is the only source providing real ticket counts.",
        },
        {
            "name": "jkt48_official",
            "label": "jkt48.com (official website)",
            "base_url": "https://jkt48.com",
            "docs_url": "https://jkt48.com",
            "auth": "none",
            "capabilities": {
                "members": "unsupported",
                "events": "unsupported",
                "schedules": "unsupported",
                "ticket_stock": "unsupported",
                "ticket_stock_history": "unsupported",
            },
            "notes": (
                "No documented public API. Responses are HTTP 403 to automated "
                "clients and scraping was intentionally not implemented."
            ),
        },
        {
            "name": "jkt48connect",
            "label": "JKT48Connect API",
            "base_url": "https://v2.jkt48connect.com",
            "docs_url": "https://docs.jkt48connect.com/",
            "auth": "apikey query parameter",
            "capabilities": {
                "members": "documented",
                "events": "documented",
                "schedules": "documented",
                "ticket_stock": "not documented",
                "ticket_stock_history": "not documented",
            },
            "notes": (
                "Host did not resolve during verification and no ticket-stock "
                "endpoints are documented. Not enabled."
            ),
        },
    ]


def source_states(connector: BaseConnector | None = None, *, available: bool | None = None,
                  message: str | None = None) -> list[SourceState]:
    conn = connector or get_connector()
    states = [conn.describe(available=available, message=message)]
    for source in documented_sources():
        if source["name"] == conn.name:
            continue
        stock = source["capabilities"].get("ticket_stock", "unsupported")
        states.append(
            SourceState(
                name=source["name"],
                configured=False,
                available=False,
                supported_features=[
                    k for k, v in source["capabilities"].items()
                    if v in ("supported", "documented")
                ],
                message=(
                    "Not enabled. " + source["notes"]
                    if stock == "unsupported"
                    else "Not enabled. " + source["notes"]
                ),
                base_url=source["base_url"],
                docs_url=source["docs_url"],
            )
        )
    return states
