from uuid import uuid4

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
        "/api/workspaces",
        "/api/workspaces/{workspace_id}",
        "/api/workspaces/{workspace_id}/wallets",
        "/api/workspaces/{workspace_id}/wallets/{wallet_id}",
        "/api/workspaces/{workspace_id}/categories",
        "/api/workspaces/{workspace_id}/categories/{category_id}",
        "/api/workspaces/{workspace_id}/transactions",
        "/api/workspaces/{workspace_id}/topups",
        "/api/workspaces/{workspace_id}/topups/{topup_id}",
        "/api/workspaces/{workspace_id}/transactions/{transaction_id}",
        "/api/workspaces/{workspace_id}/analytics",
        "/api/workspaces/{workspace_id}/wallets/{wallet_id}/rates",
    ]:
        assert path in paths, path


def test_icons_endpoint_returns_full_sorted_list_without_auth() -> None:
    response = TestClient(app).get("/api/icons")

    assert response.status_code == 200
    body = response.json()
    assert body == sorted(body)
    assert "wallet" in body


def test_workspace_schemas_expose_currency_id() -> None:
    schemas = TestClient(app).get("/openapi.json").json()["components"]["schemas"]

    assert "currency_id" in schemas["WorkspaceOut"]["required"]
    assert "currency_id" in schemas["WorkspaceCreate"]["required"]
    assert "currency_id" not in schemas["WorkspaceUpdate"].get("required", [])


def test_wallet_schemas_expose_single_currency_id() -> None:
    schemas = TestClient(app).get("/openapi.json").json()["components"]["schemas"]

    assert "currency_id" in schemas["WalletOut"]["required"]
    assert "currency_ids" not in schemas["WalletOut"]["properties"]
    assert "currency_id" in schemas["WalletCreate"]["required"]
    assert "currency_ids" not in schemas["WalletCreate"]["properties"]


def test_topups_are_a_separate_resource() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    assert set(paths["/api/workspaces/{workspace_id}/topups"]) == {"get", "post"}
    assert set(paths["/api/workspaces/{workspace_id}/topups/{topup_id}"]) == {"get", "put", "delete"}
    assert "/api/workspaces/{workspace_id}/transactions/topups" not in paths


def test_topups_require_authentication() -> None:
    response = TestClient(app).get(f"/api/workspaces/{uuid4()}/topups")

    assert response.status_code == 401


def test_expense_request_has_no_currency_id() -> None:
    schemas = TestClient(app).get("/openapi.json").json()["components"]["schemas"]

    assert "currency_id" not in schemas["TransactionCreate"]["properties"]
    assert set(schemas["TransactionCreate"]["required"]) == {"wallet_id", "category_id", "amount"}
    assert "currency_id" in schemas["TransactionLegOut"]["required"]


def test_expenses_require_authentication() -> None:
    response = TestClient(app).post(
        f"/api/workspaces/{uuid4()}/transactions",
        json={"wallet_id": str(uuid4()), "category_id": str(uuid4()), "amount": "1"},
    )

    assert response.status_code == 401


def test_wallet_rates_endpoint_has_no_target_currency_parameter() -> None:
    openapi = TestClient(app).get("/openapi.json").json()
    operation = openapi["paths"]["/api/workspaces/{workspace_id}/wallets/{wallet_id}/rates"]["get"]
    schema = openapi["components"]["schemas"]["WalletRateOut"]

    assert "target_currency_id" not in {parameter["name"] for parameter in operation["parameters"]}
    assert set(schema["required"]) == {"workspace_currency_id", "wallet_currency_id", "rate"}


def test_analytics_display_currency_and_dates_are_optional() -> None:
    openapi = TestClient(app).get("/openapi.json").json()
    parameters = openapi["paths"]["/api/workspaces/{workspace_id}/analytics"]["get"]["parameters"]
    required = {parameter["name"] for parameter in parameters if parameter["required"]}

    assert not {"display_currency", "date_from", "date_to"} & required
    assert "group_by" in required
