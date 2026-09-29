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


def test_auth_routes_are_registered() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    for path in [
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/password",
        "/api/auth/me",
        "/api/currencies",
        "/api/icons",
        "/api/wallets",
        "/api/wallets/{wallet_id}",
    ]:
        assert path in paths, path


def test_icons_endpoint_returns_full_sorted_list_without_auth() -> None:
    response = TestClient(app).get("/api/icons")

    assert response.status_code == 200
    body = response.json()
    assert body == sorted(body)
    assert "wallet" in body
