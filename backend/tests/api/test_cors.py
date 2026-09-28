from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import create_app
from utils.configure_cors import configure_cors

ALLOWED = "https://app.example.com"
FOREIGN = "https://evil.example"


def _client() -> TestClient:
    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_allowed_origin_gets_cors_headers_with_credentials() -> None:
    response = _client().get("/health", headers={"Origin": ALLOWED})

    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_from_allowed_origin() -> None:
    response = _client().options(
        "/health",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_foreign_origin_gets_no_cors_headers() -> None:
    response = _client().get("/health", headers={"Origin": FOREIGN})

    # Starlette добавляет access-control-allow-credentials на любой запрос с Origin, но без allow-origin
    # браузер такой ответ frontend'у не отдаёт.
    assert "access-control-allow-origin" not in response.headers


def test_404_has_cors_headers() -> None:
    response = _client().get("/nope", headers={"Origin": ALLOWED})

    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"


def test_400_has_cors_headers() -> None:
    response = _client().get("/health?x=1", headers={"Origin": ALLOWED})
    assert response.status_code == 200

    app = create_app()

    @app.get("/need-int")
    async def need_int(value: int) -> None: ...

    response = TestClient(app).get("/need-int?value=abc", headers={"Origin": ALLOWED})

    assert response.status_code == 400
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_500_has_cors_headers_and_json_body() -> None:
    response = _client().get("/boom", headers={"Origin": ALLOWED})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"


def test_empty_origins_do_not_enable_cors() -> None:
    app = FastAPI()
    configure_cors(app, [])

    @app.get("/x")
    async def x() -> dict[str, str]:
        return {}

    response = TestClient(app).get("/x", headers={"Origin": ALLOWED})

    assert "access-control-allow-origin" not in response.headers
