from uuid import uuid4

import pytest

from core.entities import Currency
from core.exceptions import ClientError, NotFoundError
from core.services.wallet import WalletService
from tests.fakes import FixedClock, InMemoryCurrencyRepository, InMemoryWalletRepository, SequentialIdGenerator


async def make_service(
    known_currencies: list[Currency] | None = None,
) -> tuple[WalletService, InMemoryWalletRepository, InMemoryCurrencyRepository]:
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    if known_currencies:
        await currencies.upsert_many(known_currencies)
    service = WalletService(wallets, currencies, FixedClock(), SequentialIdGenerator())
    return service, wallets, currencies


def make_currency(code: str = "RUB") -> Currency:
    return Currency(id=uuid4(), code=code, name=code, decimal_places=2)


async def test_create_wallet_with_single_currency() -> None:
    currency = make_currency("RUB")
    service, _, _ = await make_service([currency])
    user_id = uuid4()

    wallet = await service.create_wallet(user_id, name="Наличные", icon="wallet", currency_ids=[currency.id])

    assert wallet.user_id == user_id
    assert wallet.name == "Наличные"
    assert wallet.currency_ids == (currency.id,)
    assert wallet.created_at is not None


async def test_create_wallet_with_multiple_currencies() -> None:
    rub, cny = make_currency("RUB"), make_currency("CNY")
    service, _, _ = await make_service([rub, cny])
    user_id = uuid4()

    wallet = await service.create_wallet(user_id, name="Мультивалютный", icon="wallet", currency_ids=[rub.id, cny.id])

    assert set(wallet.currency_ids) == {rub.id, cny.id}


async def test_create_wallet_rejects_unknown_currency() -> None:
    known = make_currency("RUB")
    unknown_id = uuid4()
    service, _, _ = await make_service([known])

    with pytest.raises(ClientError) as exc_info:
        await service.create_wallet(uuid4(), name="Кошелёк", icon="wallet", currency_ids=[known.id, unknown_id])

    assert str(unknown_id) in exc_info.value.message


async def test_get_wallet_unknown_id_raises_not_found() -> None:
    service, _, _ = await make_service()

    with pytest.raises(NotFoundError):
        await service.get_wallet(uuid4(), uuid4())


async def test_get_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_ids=[currency.id])

    with pytest.raises(NotFoundError):
        await service.get_wallet(wallet.id, uuid4())


async def test_update_wallet_replaces_currency_set() -> None:
    rub, cny, usdt = make_currency("RUB"), make_currency("CNY"), make_currency("USDT")
    service, _, _ = await make_service([rub, cny, usdt])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_ids=[rub.id])

    updated = await service.update_wallet(
        wallet.id, owner, name="Новое имя", icon="banknote", currency_ids=[cny.id, usdt.id]
    )

    assert updated.name == "Новое имя"
    assert updated.icon == "banknote"
    assert set(updated.currency_ids) == {cny.id, usdt.id}
    assert updated.updated_at is not None


async def test_update_wallet_unknown_id_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])

    with pytest.raises(NotFoundError):
        await service.update_wallet(uuid4(), uuid4(), name="X", icon="wallet", currency_ids=[currency.id])


async def test_update_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_ids=[currency.id])

    with pytest.raises(NotFoundError):
        await service.update_wallet(wallet.id, uuid4(), name="X", icon="wallet", currency_ids=[currency.id])


async def test_delete_wallet_unknown_id_raises_not_found() -> None:
    service, _, _ = await make_service()

    with pytest.raises(NotFoundError):
        await service.delete_wallet(uuid4(), uuid4())


async def test_delete_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_ids=[currency.id])

    with pytest.raises(NotFoundError):
        await service.delete_wallet(wallet.id, uuid4())


async def test_delete_wallet_success() -> None:
    currency = make_currency()
    service, wallets, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_ids=[currency.id])

    await service.delete_wallet(wallet.id, owner)

    assert await wallets.get_by_id(wallet.id, owner) is None


async def test_list_wallets_returns_only_given_user_wallets() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    user_a, user_b = uuid4(), uuid4()
    await service.create_wallet(user_a, name="A1", icon="wallet", currency_ids=[currency.id])
    await service.create_wallet(user_b, name="B1", icon="wallet", currency_ids=[currency.id])

    items, total = await service.list_wallets(user_a, limit=20, offset=0)

    assert total == 1
    assert [wallet.name for wallet in items] == ["A1"]
