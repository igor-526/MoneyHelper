from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Currency
from repositories.currency import CurrencyRepository

pytestmark = pytest.mark.infrastructure


def make_currency(code: str = "RUB", name: str = "Российский рубль", decimal_places: int = 2) -> Currency:
    return Currency(id=uuid4(), code=code, name=name, decimal_places=decimal_places)


async def test_upsert_many_inserts_new_records(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    currencies = [make_currency("RUB"), make_currency("CNY"), make_currency("USDT")]

    await repo.upsert_many(currencies)
    await db_session.flush()

    assert await repo.count() == 3


async def test_list_is_sorted_by_code(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    await repo.upsert_many([make_currency("RUB"), make_currency("CNY"), make_currency("USDT")])
    await db_session.flush()

    items = await repo.list(limit=20, offset=0)

    assert [item.code for item in items] == ["CNY", "RUB", "USDT"]


async def test_list_applies_pagination(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    await repo.upsert_many([make_currency("RUB"), make_currency("CNY"), make_currency("USDT")])
    await db_session.flush()

    items = await repo.list(limit=1, offset=1)

    assert [item.code for item in items] == ["RUB"]


async def test_upsert_many_updates_existing_record_by_id(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    currency = make_currency("RUB", name="Рубль")
    await repo.upsert_many([currency])
    await db_session.flush()

    updated = Currency(id=currency.id, code="RUB", name="Российский рубль", decimal_places=2)
    await repo.upsert_many([updated])
    await db_session.flush()

    items = await repo.list(limit=20, offset=0)
    assert len(items) == 1
    assert items[0].name == "Российский рубль"


async def test_upsert_many_does_not_delete_records_missing_from_batch(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    kept = make_currency("CNY")
    await repo.upsert_many([kept, make_currency("RUB")])
    await db_session.flush()

    await repo.upsert_many([kept])
    await db_session.flush()

    assert await repo.count() == 2


async def test_upsert_many_with_empty_sequence_is_noop(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)

    await repo.upsert_many([])
    await db_session.flush()

    assert await repo.count() == 0


async def test_missing_ids_with_all_known_ids_returns_empty_set(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    rub, cny = make_currency("RUB"), make_currency("CNY")
    await repo.upsert_many([rub, cny])
    await db_session.flush()

    assert await repo.missing_ids([rub.id, cny.id]) == set()


async def test_missing_ids_returns_only_unknown_ids(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    rub = make_currency("RUB")
    await repo.upsert_many([rub])
    await db_session.flush()
    unknown_id = uuid4()

    assert await repo.missing_ids([rub.id, unknown_id]) == {unknown_id}


async def test_missing_ids_with_empty_input_returns_empty_set(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)

    assert await repo.missing_ids([]) == set()


async def test_get_by_id_returns_existing_currency(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)
    currency = make_currency("RUB")
    await repo.upsert_many([currency])
    await db_session.flush()

    fetched = await repo.get_by_id(currency.id)

    assert fetched is not None
    assert fetched.code == "RUB"


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = CurrencyRepository(db_session)

    assert await repo.get_by_id(uuid4()) is None
