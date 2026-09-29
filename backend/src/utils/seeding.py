import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from core.entities import Entity

SEEDING_LOCK_KEY = "moneyhelper:seeding"


class UpsertRepository[T](Protocol):
    async def upsert_many(self, items: Sequence[T]) -> None: ...


@dataclass(frozen=True)
class SeedSource[T: Entity]:
    path: Path
    parse_row: Callable[[dict[str, Any]], T]


@dataclass(frozen=True)
class SeedDefinition[T: Entity]:
    source: SeedSource[T]
    repository_factory: Callable[[AsyncSession], UpsertRepository[T]]


async def seed_from_json[T: Entity](source: SeedSource[T], repository: UpsertRepository[T]) -> None:
    """DB-агностичная часть: читает JSON, валидирует, вызывает repository.upsert_many. Тестируется на fake."""
    rows = json.loads(source.path.read_text(encoding="utf-8"))
    await repository.upsert_many([source.parse_row(row) for row in rows])


async def run_seeding(engine: AsyncEngine, definitions: Sequence[SeedDefinition[Any]]) -> None:
    """Инфраструктурная часть: один advisory lock на весь набор источников, вызывается из lifespan."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_lock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            for definition in definitions:
                await seed_from_json(definition.source, definition.repository_factory(session))
            await session.commit()
            # `pg_advisory_lock` перед созданием сессии уже открыл транзакцию на connection (autobegin);
            # session.commit() при join_transaction_mode="conditional_savepoint" коммитит только вложенный
            # savepoint, а не эту внешнюю транзакцию — без явного connection.commit() изменения теряются
            # при закрытии соединения (implicit rollback).
            await connection.commit()
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})
