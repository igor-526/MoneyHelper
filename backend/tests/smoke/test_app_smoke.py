import pytest
from fastapi.testclient import TestClient

from main import app

pytestmark = pytest.mark.smoke


def test_app_starts_and_serves_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_generated() -> None:
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
