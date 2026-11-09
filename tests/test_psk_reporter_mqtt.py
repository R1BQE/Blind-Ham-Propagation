import pytest

from backend.app.collectors.psk_reporter_mqtt import (
    DEFAULT_TOPIC_FILTERS,
    MQTTConfig,
    PSKReporterCollector,
)


@pytest.fixture(autouse=True)
def isolate_settings_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.collectors.psk_reporter_mqtt.SETTINGS_PATH",
        tmp_path / "settings.ini",
    )


class FakeStore:
    def __init__(self):
        self.items = []

    def add_spot(self, spot, *, received_at=None):
        if any(item["sequence"] == spot["sequence"] for item in self.items):
            return False
        self.items.append({**spot, "received_at": received_at})
        return True

    def count(self):
        return len(self.items)


TOPIC = "pskr/filter/v2/20m/FT8/R1BQE/W1ABC/KO59XX/FN31pr/54/291"
PAYLOAD = (
    b'{"sq":12345,"f":14074653,"md":"FT8","rp":-5,'
    b'"t":1794254400,"t_tx":1794254388}'
)


def test_default_collector_is_disabled_and_uses_narrow_pilot_topic():
    config = MQTTConfig()
    collector = PSKReporterCollector(config, store=FakeStore())

    collector.start()
    status = collector.status()

    assert DEFAULT_TOPIC_FILTERS == ("pskr/filter/v2/20m/FT8/#",)
    assert status["enabled"] is False
    assert status["state"] == "disabled"
    assert status["topic_filters"] == ["pskr/filter/v2/20m/FT8/#"]


def test_collector_saves_normalized_spot_and_counts_duplicate():
    store = FakeStore()
    collector = PSKReporterCollector(
        MQTTConfig(enabled=True),
        store=store,
    )

    collector._handle_message(TOPIC, PAYLOAD)
    collector._handle_message(TOPIC, PAYLOAD)

    status = collector.status()
    assert status["messages_received"] == 2
    assert status["spots_saved"] == 1
    assert status["duplicates"] == 1
    assert status["stored_spots"] == 1
    assert store.items[0]["tx_call"] == "R1BQE"
    assert store.items[0]["rx_call"] == "W1ABC"


def test_collector_counts_malformed_messages_without_stopping():
    collector = PSKReporterCollector(
        MQTTConfig(enabled=True),
        store=FakeStore(),
    )

    collector._handle_message("wrong/topic", b"not-json")

    status = collector.status()
    assert status["messages_received"] == 1
    assert status["invalid_messages"] == 1
    assert status["spots_saved"] == 0


def test_environment_enables_collector_in_local_session_by_default(monkeypatch):
    monkeypatch.delenv("PSK_REPORTER_ENABLED", raising=False)
    monkeypatch.setenv("BLIND_HAM_LOCAL_SESSION", "1")

    config = MQTTConfig.from_environment()

    assert config.enabled is True


def test_environment_keeps_collector_disabled_outside_local_session(monkeypatch):
    monkeypatch.delenv("PSK_REPORTER_ENABLED", raising=False)
    monkeypatch.delenv("BLIND_HAM_LOCAL_SESSION", raising=False)

    config = MQTTConfig.from_environment()

    assert config.enabled is False


def test_explicit_environment_setting_overrides_local_default(monkeypatch):
    monkeypatch.setenv("BLIND_HAM_LOCAL_SESSION", "1")
    monkeypatch.setenv("PSK_REPORTER_ENABLED", "false")

    config = MQTTConfig.from_environment()

    assert config.enabled is False


def test_explicit_environment_setting_can_enable_collector(monkeypatch):
    monkeypatch.delenv("BLIND_HAM_LOCAL_SESSION", raising=False)
    monkeypatch.setenv("PSK_REPORTER_ENABLED", "true")

    config = MQTTConfig.from_environment()

    assert config.enabled is True


def test_environment_topics_are_validated(monkeypatch):
    monkeypatch.setenv("PSK_REPORTER_ENABLED", "true")
    monkeypatch.setenv(
        "PSK_REPORTER_TOPICS",
        "pskr/filter/v2/20m/FT8/#,pskr/filter/v2/40m/FT8/#",
    )

    config = MQTTConfig.from_environment()

    assert config.enabled is True
    assert len(config.topic_filters) == 2


def test_environment_rejects_unrelated_mqtt_topics(monkeypatch):
    monkeypatch.setenv("PSK_REPORTER_TOPICS", "some/other/topic")

    try:
        MQTTConfig.from_environment()
    except ValueError as exc:
        assert "pskr/filter/v2/" in str(exc)
    else:
        raise AssertionError("Invalid topic filter was accepted")
