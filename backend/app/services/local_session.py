"""Track the local browser session and stop the local server after tab close."""
from __future__ import annotations

import asyncio
import time
from typing import Any

HEARTBEAT_TIMEOUT_SECONDS = 25
SHUTDOWN_GRACE_SECONDS = 20

_last_heartbeat = time.monotonic()
_shutdown_task: asyncio.Task[None] | None = None


def heartbeat() -> None:
    """Mark the local browser page as active."""
    global _last_heartbeat
    _last_heartbeat = time.monotonic()


async def request_shutdown_after_page_close(app: Any) -> None:
    """Stop Uvicorn if no page heartbeat arrives during the grace period."""
    global _shutdown_task

    if _shutdown_task is not None and not _shutdown_task.done():
        return

    async def wait_for_close() -> None:
        await asyncio.sleep(SHUTDOWN_GRACE_SECONDS)
        if time.monotonic() - _last_heartbeat >= HEARTBEAT_TIMEOUT_SECONDS:
            server = getattr(app.state, "uvicorn_server", None)
            if server is not None:
                server.should_exit = True

    _shutdown_task = asyncio.create_task(wait_for_close())
