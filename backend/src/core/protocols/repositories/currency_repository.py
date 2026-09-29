from collections.abc import Sequence
from typing import Protocol

from core.entities import Currency


class CurrencyRepository(Protocol):
    async def list(self, *, limit: int, offset: int) -> list[Currency]: ...

    async def count(self) -> int: ...

    async def upsert_many(self, currencies: Sequence[Currency]) -> None:
        """Добавляет отсутствующие и обновляет code/name/decimal_places у существующих по id.
        Не удаляет записи, которых нет в currencies."""
        ...
