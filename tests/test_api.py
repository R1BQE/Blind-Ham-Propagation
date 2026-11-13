from fastapi.testclient import TestClient

from backend.app.main import app

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


def test_regional_psk_report_endpoint(monkeypatch):
    class EmptyStore:
        def list_recent(self, *, now=None, limit=1000, band=None):
            return []

    monkeypatch.setenv("PSK_REPORTER_ENABLED", "false")
    monkeypatch.setattr("backend.app.api.routes.SpotStore", EmptyStore)
    with TestClient(app) as running_client:
        response = running_client.get(
            "/api/v1/psk-reporter/regional",
            params={"locator": "KP50DB", "radius_km": 100, "hours": 6},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["locator"] == "KP50DB"
    assert payload["radius_km"] == 100
    assert payload["tx"]["spots"] == 0
    assert payload["rx"]["spots"] == 0


def test_regional_psk_report_rejects_invalid_locator(monkeypatch):
    monkeypatch.setenv("PSK_REPORTER_ENABLED", "false")
    with TestClient(app) as running_client:
        response = running_client.get(
            "/api/v1/psk-reporter/regional",
            params={"locator": "NOTVALID"},
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
