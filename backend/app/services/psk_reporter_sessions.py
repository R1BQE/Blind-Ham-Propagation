"""Coordinate one shared PSK Reporter collector across browser viewers."""
from __future__ import annotations

import asyncio
import logging

from backend.app.collectors.psk_reporter_mqtt import PSKReporterCollector

logger = logging.getLogger(__name__)


class PSKReporterSessions:
    """Start on the first viewer and stop after the last viewer leaves."""

    def __init__(self, collector: PSKReporterCollector, *, idle_timeout: float = 20.0):
        self.collector = collector
        self.idle_timeout = idle_timeout
        self._viewers: set[int] = set()
        self._lock = asyncio.Lock()
        self._stop_task: asyncio.Task[None] | None = None

    async def connect(self, connection_id: int) -> None:
        async with self._lock:
            if self._stop_task is not None:
                self._stop_task.cancel()
                self._stop_task = None
            first_viewer = not self._viewers
            self._viewers.add(connection_id)
            if first_viewer and self.collector.config.enabled:
                await asyncio.to_thread(self.collector.start)
                logger.info("PSK Reporter collection started (%d viewers)", len(self._viewers))

    async def disconnect(self, connection_id: int) -> None:
        async with self._lock:
            self._viewers.discard(connection_id)
            if self._viewers or not self.collector.config.enabled:
                return
            if self._stop_task is not None:
                self._stop_task.cancel()
            self._stop_task = asyncio.create_task(self._stop_when_idle())

    async def _stop_when_idle(self) -> None:
        try:
            await asyncio.sleep(self.idle_timeout)
            async with self._lock:
                if self._viewers:
                    return
                await asyncio.to_thread(self.collector.stop)
                logger.info("PSK Reporter collection stopped after idle timeout")
                self._stop_task = None
        except asyncio.CancelledError:
            raise

    async def shutdown(self) -> None:
        async with self._lock:
            if self._stop_task is not None:
                self._stop_task.cancel()
                self._stop_task = None
            self._viewers.clear()
            await asyncio.to_thread(self.collector.stop)
