"""Track the local browser session and stop the local server when it disappears."""
from __future__ import annotations

import asyncio
import time
from typing import Any

HEARTBEAT_INTERVAL_SECONDS = 10
HEARTBEAT_TIMEOUT_SECONDS = 30
MONITOR_INTERVAL_SECONDS = 5

_last_heartbeat = time.monotonic()
_monitor_task: asyncio.Task[None] | None = None


def heartbeat(app: Any) -> None:
    """Mark the local browser page as active and start the watchdog."""
    global _last_heartbeat, _monitor_task
    _last_heartbeat = time.monotonic()
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(_watch_browser(app))


async def _watch_browser(app: Any) -> None:
    """Stop Uvicorn after heartbeats disappear (tab close or browser crash)."""
    while True:
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
        if time.monotonic() - _last_heartbeat < HEARTBEAT_TIMEOUT_SECONDS:
            continue
        server = getattr(app.state, "uvicorn_server", None)
        if server is not None:
            server.should_exit = True
        return


async def request_shutdown_after_page_close(app: Any) -> None:
    """Ensure the watchdog is active; the pagehide request itself is not a heartbeat."""
    global _monitor_task
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(_watch_browser(app))
