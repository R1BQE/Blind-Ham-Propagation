from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
