from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Currency
from models import currencies


def _map_row(row: Row[Any]) -> Currency:
    return Currency(id=row.id, code=row.code, name=row.name, decimal_places=row.decimal_places)


class CurrencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, limit: int, offset: int) -> list[Currency]:
        rows = await self._session.execute(select(currencies).order_by(currencies.c.code).limit(limit).offset(offset))
        return [_map_row(row) for row in rows]

    async def count(self) -> int:
        return (await self._session.execute(select(func.count()).select_from(currencies))).scalar_one()

    async def upsert_many(self, currencies_: Sequence[Currency]) -> None:
        if not currencies_:
            return
        statement = insert(currencies).values(
            [
                {
                    "id": currency.id,
                    "code": currency.code,
                    "name": currency.name,
                    "decimal_places": currency.decimal_places,
                }
                for currency in currencies_
            ]
        )
        statement = statement.on_conflict_do_update(
            index_elements=[currencies.c.id],
            set_={
                "code": statement.excluded.code,
                "name": statement.excluded.name,
                "decimal_places": statement.excluded.decimal_places,
            },
        )
        await self._session.execute(statement)

    async def missing_ids(self, currency_ids: Sequence[UUID]) -> set[UUID]:
        if not currency_ids:
            return set()
        rows = await self._session.execute(select(currencies.c.id).where(currencies.c.id.in_(currency_ids)))
        existing_ids = {row.id for row in rows}
        return {currency_id for currency_id in currency_ids if currency_id not in existing_ids}
