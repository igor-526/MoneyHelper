from typing import Any

import pytest

from tests.testing_settings import DatabaseTestSettings, apply_test_database_env


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TEST_POSTGRES_DB", "TEST_POSTGRES_HOST", "TEST_POSTGRES_PORT"):
        monkeypatch.delenv(name, raising=False)


def _settings(db: str | None = None, host: str | None = None, port: int | None = None) -> DatabaseTestSettings:
    values: dict[str, Any] = {}
    if db:
        values["test_postgres_db"] = db
    if host:
        values["test_postgres_host"] = host
    if port:
        values["test_postgres_port"] = port
    return DatabaseTestSettings.model_construct(**values)


def test_test_database_replaces_dev_database() -> None:
    env = {"POSTGRES_DB": "moneyhelper", "POSTGRES_HOST": "moneyhelper-db", "POSTGRES_PORT": "5432"}

    apply_test_database_env(env, _settings(db="moneyhelper_test"))

    assert env == {"POSTGRES_DB": "moneyhelper_test", "POSTGRES_HOST": "moneyhelper-db", "POSTGRES_PORT": "5432"}


def test_default_test_database_name() -> None:
    env: dict[str, str] = {}

    apply_test_database_env(env, _settings())

    assert env == {"POSTGRES_DB": "app_test"}


def test_test_host_and_port_override_dev_values() -> None:
    env = {"POSTGRES_HOST": "moneyhelper-db", "POSTGRES_PORT": "5432"}

    apply_test_database_env(env, _settings(host="localhost", port=5471))

    assert env["POSTGRES_HOST"] == "localhost"
    assert env["POSTGRES_PORT"] == "5471"
