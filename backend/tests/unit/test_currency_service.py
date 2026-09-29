from uuid import uuid4

from core.entities import Currency
from core.services.currency import CurrencyService
from tests.fakes import InMemoryCurrencyRepository


def make_currency(code: str, name: str = "Валюта", decimal_places: int = 2) -> Currency:
    return Currency(id=uuid4(), code=code, name=name, decimal_places=decimal_places)


async def test_list_currencies_returns_items_and_total() -> None:
    repository = InMemoryCurrencyRepository()
    await repository.upsert_many([make_currency("RUB"), make_currency("CNY"), make_currency("USDT")])
    service = CurrencyService(repository)

    items, total = await service.list_currencies(limit=20, offset=0)

    assert [currency.code for currency in items] == ["CNY", "RUB", "USDT"]
    assert total == 3


async def test_list_currencies_applies_pagination() -> None:
    repository = InMemoryCurrencyRepository()
    await repository.upsert_many([make_currency("RUB"), make_currency("CNY"), make_currency("USDT")])
    service = CurrencyService(repository)

    items, total = await service.list_currencies(limit=1, offset=1)

    assert [currency.code for currency in items] == ["RUB"]
    assert total == 3


async def test_list_currencies_empty_repository() -> None:
    service = CurrencyService(InMemoryCurrencyRepository())

    items, total = await service.list_currencies(limit=20, offset=0)

    assert items == []
    assert total == 0
