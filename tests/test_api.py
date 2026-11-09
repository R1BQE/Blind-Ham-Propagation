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
