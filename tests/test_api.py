import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

@pytest.fixture(autouse=True)
def isolate_collector_settings_file(tmp_path, monkeypatch):
    # TestClient lifespan constructs the MQTT collector. Keep its settings path
    # inside the temporary test directory so tests cannot touch production config.
    monkeypatch.setattr(
        "backend.app.collectors.psk_reporter_mqtt.SETTINGS_PATH",
        tmp_path / "settings.ini",
    )


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_psk_reporter_status_endpoint_starts_disabled_collector(monkeypatch):
    monkeypatch.setenv("PSK_REPORTER_ENABLED", "false")
    with TestClient(app) as running_client:
        response = running_client.get("/api/v1/psk-reporter/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["state"] == "disabled"


def test_locator_validation_endpoint():
    response = client.post(
        "/api/v1/locator/validate",
        json={"locator": "KO59XX"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["locator"] == "KO59XX"
    assert payload["latitude"] == 59.979167
    assert payload["longitude"] == 31.958333


def test_invalid_locator_returns_validation_error():
    response = client.post(
        "/api/v1/locator/validate",
        json={"locator": "KO59!X"},
    )
    assert response.status_code == 422


def test_legacy_historical_regional_endpoint_is_removed():
    response = client.get(
        "/api/v1/psk-reporter/regional",
        params={"locator": "KP50DB"},
    )
    assert response.status_code == 404


def test_offline_geography_lookup_endpoint(monkeypatch):
    class FakeGeographyDatabase:
        def lookup(self, latitude, longitude):
            assert latitude == pytest.approx(59.979167)
            assert longitude == pytest.approx(31.958333)
            return {
                "country": "Россия",
                "region": "Ленинградская область",
                "settlement": "Тестовый город",
                "settlement_distance_km": 1.2,
                "text": "Россия, Ленинградская область, Тестовый город",
            }

    monkeypatch.setattr(
        "backend.app.api.routes.get_geography_database",
        lambda: FakeGeographyDatabase(),
    )

    response = client.post(
        "/api/v1/geography/lookup",
        json={"locators": ["ko59xx", "KO59XX"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    assert payload["results"][0]["locator"] == "KO59XX"
    assert payload["results"][0]["settlement"] == "Тестовый город"
    assert "GeoNames" in payload["attribution"]


def test_offline_geography_lookup_rejects_invalid_locator():
    response = client.post(
        "/api/v1/geography/lookup",
        json={"locators": ["KO59!X"]},
    )
    assert response.status_code == 422


def test_offline_geography_lookup_rejects_empty_batch():
    response = client.post(
        "/api/v1/geography/lookup",
        json={"locators": []},
    )
    assert response.status_code == 422


def test_coordinate_locator_endpoint_selects_precision():
    response = client.post(
        "/api/v1/locator/from-coordinates",
        json={"latitude": 59.94, "longitude": 30.31, "accuracy_m": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["locator"]) == 10
    assert payload["precision"] == 10
    assert payload["accuracy_m"] == 5


def test_coordinate_locator_endpoint_rejects_invalid_coordinates():
    response = client.post(
        "/api/v1/locator/from-coordinates",
        json={"latitude": 95, "longitude": 30, "accuracy_m": 10},
    )
    assert response.status_code == 422


def test_public_config_reads_yandex_key_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("YANDEX_MAPS_JS_API_KEY", "test-browser-key")
    monkeypatch.setattr(
        "backend.app.api.routes.SETTINGS_PATH",
        tmp_path / "settings.ini",
    )
    response = client.get("/api/v1/config/public")
    assert response.status_code == 200
    assert response.json() == {
        "yandex_maps_enabled": True,
        "yandex_maps_api_key": "test-browser-key",
    }


def test_public_config_reads_yandex_key_from_settings_file(monkeypatch, tmp_path):
    monkeypatch.delenv("YANDEX_MAPS_JS_API_KEY", raising=False)
    settings_path = tmp_path / "settings.ini"
    settings_path.write_text(
        "[yandex_maps]\njavascript_api_key = test-file-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("backend.app.api.routes.SETTINGS_PATH", settings_path)

    response = client.get("/api/v1/config/public")

    assert response.status_code == 200
    assert response.json() == {
        "yandex_maps_enabled": True,
        "yandex_maps_api_key": "test-file-key",
    }


def test_public_config_reports_maps_disabled_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("YANDEX_MAPS_JS_API_KEY", raising=False)
    monkeypatch.setattr(
        "backend.app.api.routes.SETTINGS_PATH",
        tmp_path / "settings.ini",
    )
    response = client.get("/api/v1/config/public")
    assert response.status_code == 200
    assert response.json()["yandex_maps_enabled"] is False
    assert response.json()["yandex_maps_api_key"] == ""

def test_lifespan_starts_collector_independently_of_browser_sessions(monkeypatch):
    class FakeCollector:
        instance = None

        def __init__(self):
            self.starts = 0
            self.stops = 0
            FakeCollector.instance = self

        def start(self):
            self.starts += 1

        def stop(self):
            self.stops += 1

        def status(self):
            return {"enabled": True, "state": "connected"}

    monkeypatch.setattr("backend.app.main.PSKReporterCollector", FakeCollector)

    with TestClient(app) as running_client:
        response = running_client.get("/api/v1/psk-reporter/status")
        assert response.status_code == 200
        assert response.json()["state"] == "connected"
        assert FakeCollector.instance.starts == 1

    assert FakeCollector.instance.stops == 1



def test_regional_session_api_starts_and_reports_progress(monkeypatch):
    class FakeCollector:
        def __init__(self):
            self.spot_observer = None

        def start(self):
            pass

        def stop(self):
            pass

        def is_connected(self):
            return True

    monkeypatch.setattr("backend.app.main.PSKReporterCollector", FakeCollector)
    with TestClient(app) as running_client:
        started = running_client.post(
            "/api/v1/psk-reporter/regional/sessions",
            json={"locator": "KO59", "radius_km": 500},
        )
        assert started.status_code == 200
        session_id = started.json()["session_id"]
        progress = running_client.get(
            f"/api/v1/psk-reporter/regional/sessions/{session_id}"
        )

    assert progress.status_code == 200
    assert progress.json()["state"] == "collecting"
    assert progress.json()["locator"] == "KO59"


def test_regional_session_api_requires_connected_mqtt(monkeypatch):
    class FakeCollector:
        def __init__(self):
            self.spot_observer = None

        def start(self):
            pass

        def stop(self):
            pass

        def is_connected(self):
            return False

    monkeypatch.setattr("backend.app.main.PSKReporterCollector", FakeCollector)
    with TestClient(app) as running_client:
        response = running_client.post(
            "/api/v1/psk-reporter/regional/sessions",
            json={"locator": "KO59", "radius_km": 500},
        )
    assert response.status_code == 503
