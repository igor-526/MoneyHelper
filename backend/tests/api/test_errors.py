import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator

import utils.unhandled_error_middleware as middleware_module
from core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    ClientError,
    NotFoundError,
    PermissionDeniedError,
)
from main import create_app


class Payload(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_bad(cls, value: str) -> str:
        if value == "bad":
            raise ValueError("bad name")
        return value


def _app() -> FastAPI:
    app = create_app()

    @app.get("/raise/{kind}")
    async def raise_error(kind: str) -> None:
        errors = {
            "client": ClientError("Некорректный запрос"),
            "auth": AuthenticationError("Требуется вход"),
            "forbidden": PermissionDeniedError("Доступ запрещён"),
            "not-found": NotFoundError("Не найдено"),
            "exists": AlreadyExistsError("Уже существует"),
        }
        if kind == "unexpected":
            raise RuntimeError("secret internals")
        raise errors[kind]

    @app.post("/payload")
    async def payload(data: Payload) -> Payload:
        return data

    return app


@pytest.mark.parametrize(
    ("kind", "status", "message"),
    [
        ("client", 400, "Некорректный запрос"),
        ("auth", 401, "Требуется вход"),
        ("forbidden", 403, "Доступ запрещён"),
        ("not-found", 404, "Не найдено"),
        ("exists", 409, "Уже существует"),
    ],
)
def test_app_errors_are_mapped_to_status_codes(kind: str, status: int, message: str) -> None:
    response = TestClient(_app()).get(f"/raise/{kind}")

    assert response.status_code == status
    assert response.json() == {"detail": message}


def test_unknown_route_returns_json_404() -> None:
    response = TestClient(_app()).get("/nope")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_unsupported_method_returns_json_405() -> None:
    response = TestClient(_app()).post("/health")

    assert response.status_code == 405
    assert "detail" in response.json()


def test_validation_error_with_exception_in_ctx_returns_400() -> None:
    response = TestClient(_app()).post("/payload", json={"name": "bad"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert "bad name" in str(detail)


def test_validation_error_for_missing_field_returns_400() -> None:
    response = TestClient(_app()).post("/payload", json={})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], list)


def test_unexpected_exception_returns_500_without_details(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    captured: list[BaseException] = []
    monkeypatch.setattr(middleware_module.sentry_sdk, "capture_exception", captured.append)

    with caplog.at_level(logging.ERROR):
        response = TestClient(_app(), raise_server_exceptions=False).get("/raise/unexpected")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret internals" not in response.text
    assert len(captured) == 1 and isinstance(captured[0], RuntimeError)
    assert any("Необработанное исключение" in record.message for record in caplog.records)
