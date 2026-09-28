from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from settings import settings
from tests.infrastructure.database import TestDatabaseError, prepare_test_database


@pytest.fixture(scope="session")
def prepared_database() -> None:
    try:
        prepare_test_database()
    except TestDatabaseError as exc:
        pytest.fail(str(exc), pytrace=False)


@pytest.fixture
async def engine(prepared_database: None) -> AsyncIterator[AsyncEngine]:
    # NullPool: соединения asyncpg нельзя делить между event loop разных тестов.
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
            autoflush=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
