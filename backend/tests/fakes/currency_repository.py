from collections.abc import Sequence
from uuid import UUID

from core.entities import Currency


class InMemoryCurrencyRepository:
    def __init__(self) -> None:
        self._currencies: dict[UUID, Currency] = {}

    async def list(self, *, limit: int, offset: int) -> list[Currency]:
        items = sorted(self._currencies.values(), key=lambda currency: currency.code)
        return items[offset : offset + limit]

    async def count(self) -> int:
        return len(self._currencies)

    async def upsert_many(self, currencies: Sequence[Currency]) -> None:
        for currency in currencies:
            self._currencies[currency.id] = currency
