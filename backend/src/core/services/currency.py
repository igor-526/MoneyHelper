from core.entities import Currency
from core.protocols import CurrencyRepository


class CurrencyService:
    def __init__(self, repository: CurrencyRepository) -> None:
        self._repository = repository

    async def list_currencies(self, *, limit: int, offset: int) -> tuple[list[Currency], int]:
        items = await self._repository.list(limit=limit, offset=offset)
        total = await self._repository.count()
        return items, total
