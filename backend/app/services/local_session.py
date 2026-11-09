"""Track browser WebSocket sessions for the local development server."""
from __future__ import annotations

import asyncio
from typing import Any

SHUTDOWN_GRACE_SECONDS = 15

_active_sessions: set[int] = set()
_shutdown_task: asyncio.Task[None] | None = None


def session_connected(connection_id: int) -> None:
    """Register an open local browser tab."""
    global _shutdown_task
    _active_sessions.add(connection_id)
    if _shutdown_task is not None and not _shutdown_task.done():
        _shutdown_task.cancel()
        _shutdown_task = None


async def session_disconnected(app: Any, connection_id: int) -> None:
    """Schedule graceful shutdown after the last local browser tab closes."""
    global _shutdown_task
    _active_sessions.discard(connection_id)
    if _active_sessions:
        return
    if _shutdown_task is not None and not _shutdown_task.done():
        _shutdown_task.cancel()

    async def stop_when_unused() -> None:
        await asyncio.sleep(SHUTDOWN_GRACE_SECONDS)
        if not _active_sessions:
            server = getattr(app.state, "uvicorn_server", None)
            if server is not None:
                server.should_exit = True

    _shutdown_task = asyncio.create_task(stop_when_unused())
