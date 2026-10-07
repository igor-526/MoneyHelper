from typing import Protocol
from uuid import UUID

from core.entities import Currency


class CurrencyLookup(Protocol):
    async def get_by_id(self, currency_id: UUID) -> Currency | None: ...

    async def get_by_code(self, code: str) -> Currency | None: ...
