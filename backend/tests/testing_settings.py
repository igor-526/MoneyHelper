from collections.abc import MutableMapping

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseTestSettings(BaseSettings):
    """Параметры БД для тестов: читаются из окружения и `.env`, как и основные настройки."""

    test_postgres_db: str = "app_test"
    test_postgres_host: str | None = None
    test_postgres_port: int | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def apply_test_database_env(env: MutableMapping[str, str], test_settings: DatabaseTestSettings) -> None:
    """Подменяет параметры БД в окружении до импорта `settings`: тесты не должны видеть БД разработки."""
    env["POSTGRES_DB"] = test_settings.test_postgres_db
    if test_settings.test_postgres_host:
        env["POSTGRES_HOST"] = test_settings.test_postgres_host
    if test_settings.test_postgres_port:
        env["POSTGRES_PORT"] = str(test_settings.test_postgres_port)
