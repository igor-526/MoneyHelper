import asyncio
import re
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config

from settings import settings

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
TEST_DATABASE_NAME = re.compile(r"^[a-z0-9_]*_test$")


class TestDatabaseError(RuntimeError):
    __test__ = False


def assert_test_database_name(name: str) -> None:
    if not TEST_DATABASE_NAME.fullmatch(name):
        raise TestDatabaseError(
            f"Имя тестовой БД {name!r} недопустимо: оно должно оканчиваться на '_test' "
            "(строчные буквы, цифры, подчёркивание). Проверьте TEST_POSTGRES_DB."
        )


async def _create_database_if_missing(name: str) -> None:
    connection = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database="postgres",
    )
    try:
        exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if not exists:
            await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()


def upgrade_to_head() -> None:
    # Без ini-файла: env.py не вызывает fileConfig, поэтому логирование тестов не сбрасывается.
    config = Config()
    config.set_main_option("script_location", str(SRC_DIR / "migration"))
    command.upgrade(config, "head")


def prepare_test_database() -> None:
    name = settings.postgres_db
    assert_test_database_name(name)
    try:
        asyncio.run(_create_database_if_missing(name))
    except (OSError, asyncpg.PostgresError) as exc:
        raise TestDatabaseError(
            f"PostgreSQL недоступен ({settings.postgres_host}:{settings.postgres_port}): {exc}. "
            "Поднимите БД командой `make infra` и проверьте TEST_POSTGRES_HOST/TEST_POSTGRES_PORT."
        ) from exc
    upgrade_to_head()
