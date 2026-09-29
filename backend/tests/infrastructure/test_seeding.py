import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from models import currencies
from seeds import SEED_DEFINITIONS
from utils.seeding import SEEDING_LOCK_KEY, run_seeding

pytestmark = pytest.mark.infrastructure


@pytest.fixture(autouse=True)
async def cleanup_currencies(engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with engine.connect() as connection:
        await connection.execute(delete(currencies))
        await connection.commit()


async def test_run_seeding_creates_expected_currencies(engine: AsyncEngine) -> None:
    await run_seeding(engine, SEED_DEFINITIONS)

    async with engine.connect() as connection:
        rows = (await connection.execute(select(currencies).order_by(currencies.c.code))).all()

    assert [row.code for row in rows] == ["CNY", "RUB", "USDT"]


async def test_run_seeding_twice_does_not_duplicate(engine: AsyncEngine) -> None:
    await run_seeding(engine, SEED_DEFINITIONS)
    await run_seeding(engine, SEED_DEFINITIONS)

    async with engine.connect() as connection:
        rows = (await connection.execute(select(currencies))).all()

    assert len(rows) == 3


async def test_advisory_lock_blocks_concurrent_seeding(engine: AsyncEngine) -> None:
    async with engine.connect() as lock_connection:
        await lock_connection.execute(text("SELECT pg_advisory_lock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})

        task = asyncio.create_task(run_seeding(engine, SEED_DEFINITIONS))
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=0.5)

        async with engine.connect() as probe_connection:
            acquired = (
                await probe_connection.execute(
                    text("SELECT pg_try_advisory_lock(hashtext(:key)) AS acquired"), {"key": SEEDING_LOCK_KEY}
                )
            ).scalar_one()
        assert acquired is False

        await lock_connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})

    await asyncio.wait_for(task, timeout=5)

    async with engine.connect() as probe_connection:
        acquired_after = (
            await probe_connection.execute(
                text("SELECT pg_try_advisory_lock(hashtext(:key)) AS acquired"), {"key": SEEDING_LOCK_KEY}
            )
        ).scalar_one()
        assert acquired_after is True
        await probe_connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})
