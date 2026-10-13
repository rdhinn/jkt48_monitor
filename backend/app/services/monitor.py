"""Monitoring orchestrator: single-flight sync + notifications."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector
from app.connectors.registry import get_connector
from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import utcnow
from app.services import notifier
from app.services.sync import SyncResult, perform_sync

logger = get_logger(__name__)


class MonitorBusyError(RuntimeError):
    pass


class ManualRefreshRateLimited(RuntimeError):
    pass


class Monitor:
    """Guards against concurrent polling with an in-process lock."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.last_run_at: datetime | None = None
        self.last_success_at: datetime | None = None
        self.last_result: SyncResult | None = None
        self.last_error: str | None = None
        self.run_count = 0
        self._manual_times: deque[datetime] = deque(maxlen=32)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def running(self) -> bool:
        return self._lock.locked()

    def _check_manual_limit(self) -> None:
        now = datetime.now(timezone.utc)
        window = [t for t in self._manual_times if now - t < timedelta(minutes=1)]
        self._manual_times = deque(window, maxlen=32)
        if len(self._manual_times) >= settings.max_manual_refresh_per_minute:
            raise ManualRefreshRateLimited(
                "Manual refresh rate limit reached; please wait before retrying."
            )
        self._manual_times.append(now)

    async def run_once(
        self,
        db: AsyncSession,
        connector: BaseConnector | None = None,
        *,
        manual: bool = False,
    ) -> SyncResult:
        if manual:
            self._check_manual_limit()
        if self._lock.locked():
            raise MonitorBusyError("A monitoring run is already in progress.")
        conn = connector or get_connector()
        async with self._lock:
            self.run_count += 1
            self.last_run_at = utcnow()
            try:
                result = await perform_sync(db, conn)
                if result.changes:
                    sent = await notifier.notify_changes(
                        db, result.changes, result.rows_by_session
                    )
                    result.rows_by_session["__notifications_sent__"] = sent  # type: ignore
                self.last_result = result
                if result.success:
                    self.last_success_at = utcnow()
                    self.last_error = None
                else:
                    self.last_error = "; ".join(result.errors) or "sync failed"
                return result
            except Exception as exc:  # noqa: BLE001
                logger.exception("Monitoring run failed")
                self.last_error = str(exc)
                raise
            finally:
                try:
                    await notifier.retry_pending(db)
                except Exception:  # noqa: BLE001
                    logger.debug("retry_pending skipped", exc_info=True)

    def status(self) -> dict:
        return {
            "running": self.running,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "scheduler_enabled": settings.enable_scheduler,
        }

    async def start_background(self, session_factory) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(session_factory))

    async def stop_background(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self, session_factory) -> None:
        interval = max(15, settings.poll_interval_seconds)
        logger.info("Monitor scheduler started (interval=%ss)", interval)
        # small warm-up delay so the API can finish starting
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=5)
            return
        except asyncio.TimeoutError:
            pass
        while not self._stop.is_set():
            try:
                async with session_factory() as db:
                    await self.run_once(db)
            except MonitorBusyError:
                logger.info("Skipped scheduled run; previous run still active")
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled monitoring run failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue


monitor = Monitor()
