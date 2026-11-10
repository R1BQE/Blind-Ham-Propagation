import asyncio

from backend.app.services.psk_reporter_sessions import PSKReporterSessions


class FakeCollector:
    class Config:
        enabled = True

    config = Config()

    def __init__(self):
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1


def test_shared_collector_stops_only_after_last_viewer():
    async def scenario():
        collector = FakeCollector()
        sessions = PSKReporterSessions(collector, idle_timeout=0.01)
        await sessions.connect(1)
        await sessions.connect(2)
        assert collector.starts == 1

        await sessions.disconnect(1)
        await asyncio.sleep(0.02)
        assert collector.stops == 0

        await sessions.disconnect(2)
        stop_task = sessions._stop_task
        assert stop_task is not None
        await asyncio.wait_for(stop_task, timeout=1)
        assert collector.stops == 1

    asyncio.run(scenario())


def test_new_viewer_cancels_pending_stop():
    async def scenario():
        collector = FakeCollector()
        sessions = PSKReporterSessions(collector, idle_timeout=0.05)
        await sessions.connect(1)
        await sessions.disconnect(1)
        await sessions.connect(2)
        await asyncio.sleep(0.07)

        assert collector.starts == 2
        assert collector.stops == 0
        await sessions.shutdown()

    asyncio.run(scenario())


def test_disabled_collector_is_not_started():
    async def scenario():
        collector = FakeCollector()
        collector.config.enabled = False
        sessions = PSKReporterSessions(collector, idle_timeout=0.01)
        await sessions.connect(1)
        await sessions.disconnect(1)
        await asyncio.sleep(0.02)

        assert collector.starts == 0
        assert collector.stops == 0

    asyncio.run(scenario())
