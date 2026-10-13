"""Connector base classes and errors."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.connectors.types import (
    NormalizedEvent,
    NormalizedMember,
    NormalizedSession,
    SourceState,
)


class ConnectorError(Exception):
    """Raised when a connector cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class NotConfiguredError(ConnectorError):
    def __init__(self, message: str = "Connector is not configured") -> None:
        super().__init__(message, retryable=False)


class RateLimitedError(ConnectorError):
    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message, status_code=429, retryable=True)
        self.retry_after = retry_after


class BaseConnector(ABC):
    """Abstract data-source adapter."""

    name: str = "base"
    base_url: str = ""
    docs_url: str = ""
    supported_features: list[str] = []

    @property
    def configured(self) -> bool:
        return False

    def describe(self, *, available: bool | None = None, message: str | None = None) -> SourceState:
        if not self.configured:
            return SourceState(
                name=self.name,
                configured=False,
                available=False,
                supported_features=self.supported_features,
                message=message
                or "API key not configured. Set JKT48_API_KEY to enable this source.",
                base_url=self.base_url,
                docs_url=self.docs_url,
            )
        return SourceState(
            name=self.name,
            configured=True,
            available=bool(available) if available is not None else False,
            supported_features=self.supported_features,
            message=message,
            base_url=self.base_url,
            docs_url=self.docs_url,
        )

    @abstractmethod
    async def fetch_members(self) -> list[NormalizedMember]:
        ...

    @abstractmethod
    async def fetch_events(self) -> list[NormalizedEvent]:
        """Return schedule-level events (ticket/stock fields may be absent)."""
        ...

    @abstractmethod
    async def fetch_ticket_sales(self) -> list[NormalizedEvent]:
        """Return ticket events with per-session availability when supported."""
        ...

    @abstractmethod
    async def fetch_event_sales(self, external_id: str) -> NormalizedEvent | None:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...

    async def close(self) -> None:  # pragma: no cover - optional
        return None


# Convenience alias for typing in services/tests.
Session = NormalizedSession
