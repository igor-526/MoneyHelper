import pytest
from pydantic import ValidationError

from settings import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, value: str | None) -> Settings:
    if value is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_multiple_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, "http://localhost:5173, https://app.example.com")

    assert settings.cors_origins == ["http://localhost:5173", "https://app.example.com"]


@pytest.mark.parametrize("value", [None, ""])
def test_empty_or_missing_means_no_origins(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    assert _settings(monkeypatch, value).cors_origins == []


@pytest.mark.parametrize(
    "value",
    ["*", "app.example.com", "https://app.example.com/path", "https://app.example.com/", "ftp://app.example.com"],
)
def test_invalid_origins_are_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, value)
