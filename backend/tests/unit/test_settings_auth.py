import pytest
from pydantic import ValidationError

from settings import DEV_DEFAULT_JWT_SECRET, Settings


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str | None) -> Settings:
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ENVIRONMENT="development", REGISTRATION_ENABLED=None)

    assert settings.jwt_secret == DEV_DEFAULT_JWT_SECRET
    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 30
    assert settings.cookie_samesite == "lax"
    assert settings.registration_enabled is False
    assert settings.cookie_secure_resolved is False


def test_cookie_secure_resolved_defaults_true_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET="x" * 32)

    assert settings.cookie_secure_resolved is True


def test_cookie_secure_explicit_overrides_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET="x" * 32, COOKIE_SECURE="false")

    assert settings.cookie_secure_resolved is False


@pytest.mark.parametrize("value", ["Lax", "STRICT", "None"])
def test_cookie_samesite_is_normalized(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    kwargs = {"ENVIRONMENT": "development", "COOKIE_SAMESITE": value}
    if value.lower() == "none":
        kwargs["COOKIE_SECURE"] = "true"
    settings = _settings(monkeypatch, **kwargs)

    assert settings.cookie_samesite == value.lower()


def test_default_secret_rejected_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(monkeypatch, ENVIRONMENT="production")


def test_short_secret_rejected_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET="x" * 31)


def test_long_secret_accepted_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ENVIRONMENT="production", JWT_SECRET="x" * 32)

    assert settings.jwt_secret == "x" * 32


def test_samesite_none_requires_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="COOKIE_SAMESITE"):
        _settings(
            monkeypatch,
            ENVIRONMENT="development",
            COOKIE_SAMESITE="none",
            COOKIE_SECURE="false",
        )


def test_samesite_none_with_secure_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        monkeypatch,
        ENVIRONMENT="development",
        COOKIE_SAMESITE="none",
        COOKIE_SECURE="true",
    )

    assert settings.cookie_samesite == "none"


@pytest.mark.parametrize("value", ["0", "-1"])
def test_non_positive_ttl_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, ENVIRONMENT="development", ACCESS_TOKEN_TTL_MINUTES=value)
