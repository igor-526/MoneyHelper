import pytest

from settings import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, value: str | None) -> Settings:
    if value is None:
        monkeypatch.delenv("SEEDING_ENABLED", raising=False)
    else:
        monkeypatch.setenv("SEEDING_ENABLED", value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, None).seeding_enabled is True


def test_reads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "false").seeding_enabled is False
