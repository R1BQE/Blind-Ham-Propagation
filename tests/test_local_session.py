import asyncio
from types import SimpleNamespace

from backend.app.services import local_session


def reset_sessions():
    local_session._active_sessions.clear()
    local_session._shutdown_task = None


def test_server_stops_after_last_browser_session_closes(monkeypatch):
    async def scenario():
        reset_sessions()
        monkeypatch.setattr(local_session, "SHUTDOWN_GRACE_SECONDS", 0.01)
        server = SimpleNamespace(should_exit=False)
        app = SimpleNamespace(state=SimpleNamespace(uvicorn_server=server))

        local_session.session_connected(101)
        await local_session.session_disconnected(app, 101)
        await asyncio.sleep(0.05)

        assert server.should_exit is True

    asyncio.run(scenario())
    reset_sessions()


def test_server_stays_running_while_another_tab_is_open(monkeypatch):
    async def scenario():
        reset_sessions()
        monkeypatch.setattr(local_session, "SHUTDOWN_GRACE_SECONDS", 0.01)
        server = SimpleNamespace(should_exit=False)
        app = SimpleNamespace(state=SimpleNamespace(uvicorn_server=server))

        local_session.session_connected(101)
        local_session.session_connected(202)
        await local_session.session_disconnected(app, 101)
        await asyncio.sleep(0.03)
        assert server.should_exit is False

        await local_session.session_disconnected(app, 202)
        await asyncio.sleep(0.03)
        assert server.should_exit is True

    asyncio.run(scenario())
    reset_sessions()


def test_reopened_tab_cancels_pending_shutdown(monkeypatch):
    async def scenario():
        reset_sessions()
        monkeypatch.setattr(local_session, "SHUTDOWN_GRACE_SECONDS", 0.04)
        server = SimpleNamespace(should_exit=False)
        app = SimpleNamespace(state=SimpleNamespace(uvicorn_server=server))

        local_session.session_connected(101)
        await local_session.session_disconnected(app, 101)
        await asyncio.sleep(0.01)
        local_session.session_connected(202)
        await asyncio.sleep(0.05)

        assert server.should_exit is False

        await local_session.session_disconnected(app, 202)
        await asyncio.sleep(0.05)
        assert server.should_exit is True

    asyncio.run(scenario())
    reset_sessions()
