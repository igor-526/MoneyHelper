import threading

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from depends.auth import get_password_hasher
from depends.user import get_user_repository
from main import create_app
from settings import settings
from tests.fakes import FakePasswordHasher, InMemoryUserRepository

EMAIL = "user@example.com"
PASSWORD = "correct-horse-battery"
ALLOWED_ORIGIN = "https://app.example.com"


def make_app(repo: InMemoryUserRepository | None = None) -> FastAPI:
    app = create_app()
    repo = repo if repo is not None else InMemoryUserRepository()
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_password_hasher] = FakePasswordHasher
    return app


def make_client(repo: InMemoryUserRepository | None = None) -> TestClient:
    return TestClient(make_app(repo))


def register(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


class TestRegister:
    def test_success(self) -> None:
        response = register(make_client())

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == EMAIL
        assert "password" not in body
        assert "password_hash" not in body
        assert "token_version" not in body
        # Регистрация не устанавливает сессию.
        assert ACCESS_COOKIE_NAME not in response.cookies

    def test_normalizes_email(self) -> None:
        response = register(make_client(), email="  User@Example.COM  ")

        assert response.status_code == 201
        assert response.json()["email"] == "user@example.com"

    def test_duplicate_email_conflicts(self) -> None:
        client = make_client()
        register(client)

        response = register(client)

        assert response.status_code == 409
        assert isinstance(response.json()["detail"], str)

    def test_duplicate_email_case_insensitive(self) -> None:
        client = make_client()
        register(client, email="user@example.com")

        response = register(client, email="USER@EXAMPLE.COM")

        assert response.status_code == 409

    def test_invalid_email_is_rejected(self) -> None:
        response = register(make_client(), email="not-an-email")

        assert response.status_code == 400

    @pytest.mark.parametrize("password", ["short12", "x" * 129])
    def test_password_length_is_validated(self, password: str) -> None:
        response = register(make_client(), password=password)

        assert response.status_code == 400
        [error] = response.json()["detail"]
        assert error["loc"][-1] == "password"

    def test_disabled_registration_returns_403(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "registration_enabled", False)
        client = make_client()

        response = register(client)

        assert response.status_code == 403
        assert client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 401


class TestLogin:
    def test_success_sets_cookies_and_returns_user(self) -> None:
        client = make_client()
        register(client)

        response = login(client)

        assert response.status_code == 200
        assert response.json()["email"] == EMAIL
        assert "access_token" not in response.text
        assert "refresh_token" not in response.text
        assert ACCESS_COOKIE_NAME in response.cookies
        assert REFRESH_COOKIE_NAME in response.cookies

    def test_unknown_email_and_wrong_password_are_identical(self) -> None:
        client = make_client()
        register(client)

        unknown = login(client, email="nobody@example.com")
        wrong = login(client, password="wrong-password")

        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json() == wrong.json()

    def test_cookie_attributes(self) -> None:
        client = make_client()
        register(client)

        response = login(client)

        access_header = response.headers.get_list("set-cookie")[0]
        refresh_header = response.headers.get_list("set-cookie")[1]
        assert "HttpOnly" in access_header
        assert "Path=/;" in access_header or access_header.endswith("Path=/")
        assert "HttpOnly" in refresh_header
        assert "Path=/api/auth" in refresh_header


class TestRefresh:
    def test_success_rotates_cookies(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.post("/api/auth/refresh")

        assert response.status_code == 204
        assert ACCESS_COOKIE_NAME in response.cookies
        assert REFRESH_COOKIE_NAME in response.cookies

    def test_without_cookie_is_unauthorized(self) -> None:
        response = make_client().post("/api/auth/refresh")

        assert response.status_code == 401

    def test_parallel_refresh_both_succeed(self) -> None:
        client = make_client()
        register(client)
        login(client)

        results: list[int] = []

        def call() -> None:
            results.append(client.post("/api/auth/refresh").status_code)

        threads = [threading.Thread(target=call) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results == [204, 204]

    def test_refresh_not_sent_outside_auth_prefix(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.get("/health")

        assert REFRESH_COOKIE_NAME not in response.request.headers.get("cookie", "")


class TestLogout:
    def test_clears_cookies_and_invalidates_refresh(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.post("/api/auth/logout")
        assert response.status_code == 204

        refresh_after = client.post("/api/auth/refresh")
        assert refresh_after.status_code == 401

    def test_without_session_is_still_204(self) -> None:
        response = make_client().post("/api/auth/logout")

        assert response.status_code == 204

    def test_repeated_logout_is_idempotent(self) -> None:
        client = make_client()
        register(client)
        login(client)
        refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)
        assert refresh_token is not None

        client.post("/api/auth/logout")
        client.cookies.set(REFRESH_COOKIE_NAME, refresh_token, path="/api/auth")
        second = client.post("/api/auth/logout")

        assert second.status_code == 204


class TestMe:
    def test_requires_session(self) -> None:
        response = make_client().get("/api/auth/me")

        assert response.status_code == 401

    def test_returns_current_user(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.get("/api/auth/me")

        assert response.status_code == 200
        assert response.json()["email"] == EMAIL


class TestChangePassword:
    def test_success_rotates_session_and_password(self) -> None:
        repo = InMemoryUserRepository()
        client = make_client(repo)
        register(client)
        login(client)

        response = client.post(
            "/api/auth/password", json={"current_password": PASSWORD, "new_password": "new-password-1"}
        )

        assert response.status_code == 204
        # Сессия текущего клиента обновлена автоматически, повторный вход не нужен.
        assert client.get("/api/auth/me").status_code == 200
        # Новый пароль действует, старый — нет (другой клиент, тот же репозиторий).
        other = make_client(repo)
        assert login(other, password="new-password-1").status_code == 200
        assert login(other, password=PASSWORD).status_code == 401

    def test_wrong_current_password_rejected(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.post(
            "/api/auth/password", json={"current_password": "wrong", "new_password": "new-password-1"}
        )

        assert response.status_code == 401

    def test_requires_session(self) -> None:
        response = make_client().post(
            "/api/auth/password", json={"current_password": PASSWORD, "new_password": "new-password-1"}
        )

        assert response.status_code == 401

    def test_new_password_validated(self) -> None:
        client = make_client()
        register(client)
        login(client)

        response = client.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": "short"})

        assert response.status_code == 400

    def test_old_refresh_stops_working(self) -> None:
        repo = InMemoryUserRepository()
        client = make_client(repo)
        register(client)
        login(client)
        old_refresh = client.cookies.get(REFRESH_COOKIE_NAME)
        assert old_refresh is not None

        client.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": "new-password-1"})

        # Другое устройство с refresh, выданным до смены пароля, и тем же репозиторием на бэкенде.
        other = make_client(repo)
        other.cookies.set(REFRESH_COOKIE_NAME, old_refresh, path="/api/auth")
        assert other.post("/api/auth/refresh").status_code == 401


class TestOriginCheck:
    def _app_and_client(self) -> TestClient:
        return make_client()

    def test_allowed_origin_passes(self) -> None:
        client = self._app_and_client()

        response = client.post(
            "/api/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            headers={"Origin": ALLOWED_ORIGIN},
        )

        assert response.status_code == 401  # дошло до обработчика (пользователя нет — но не отклонено Origin)

    def test_foreign_origin_rejected_without_cors_headers(self) -> None:
        client = self._app_and_client()

        response = client.post(
            "/api/auth/logout",
            headers={"Origin": "https://evil.example"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Недопустимый источник запроса"}
        assert "access-control-allow-origin" not in response.headers
        assert ACCESS_COOKIE_NAME not in response.cookies

    def test_null_origin_rejected(self) -> None:
        response = self._app_and_client().post("/api/auth/logout", headers={"Origin": "null"})

        assert response.status_code == 403

    def test_missing_origin_is_allowed(self) -> None:
        response = self._app_and_client().post("/api/auth/logout")

        assert response.status_code == 204

    def test_safe_method_ignores_origin(self) -> None:
        response = self._app_and_client().get("/api/auth/me", headers={"Origin": "https://evil.example"})

        assert response.status_code == 401  # не 403: проверка Origin не применяется к GET

    def test_form_body_is_rejected(self) -> None:
        client = self._app_and_client()

        response = client.post(
            "/api/auth/login",
            data={"email": EMAIL, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 400
