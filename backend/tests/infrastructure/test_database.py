import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from settings import settings
from tests.infrastructure.database import TestDatabaseError, assert_test_database_name, prepare_test_database


def test_tests_use_test_database() -> None:
    assert settings.postgres_db.endswith("_test")


def test_prepare_is_idempotent(prepared_database: None) -> None:
    prepare_test_database()


@pytest.mark.parametrize("name", ["moneyhelper", "app", "app_test_", "App_test", "prod;drop_test", ""])
def test_invalid_database_name_is_rejected(name: str) -> None:
    with pytest.raises(TestDatabaseError):
        assert_test_database_name(name)


async def test_migrations_are_applied(db_session: AsyncSession) -> None:
    version = await db_session.scalar(text("SELECT version_num FROM alembic_version"))

    assert version == "20260929_0005"


async def test_commit_inside_test_is_rolled_back(db_session: AsyncSession, engine: AsyncEngine) -> None:
    await db_session.execute(text("CREATE TABLE rollback_probe (id integer)"))
    await db_session.execute(text("INSERT INTO rollback_probe VALUES (1)"))
    await db_session.commit()

    assert await db_session.scalar(text("SELECT count(*) FROM rollback_probe")) == 1

    # Вне транзакции теста запись не видна: коммит был только на уровне savepoint.
    async with engine.connect() as other:
        assert await other.scalar(text("SELECT to_regclass('rollback_probe')")) is None


async def test_previous_test_left_no_traces(db_session: AsyncSession) -> None:
    assert await db_session.scalar(text("SELECT to_regclass('rollback_probe')")) is None
