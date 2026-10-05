from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from core.entities import Currency, Transaction, TransactionLeg, Transfer
from core.exceptions import ClientError, ConflictError, NotFoundError
from core.services.wallet import WalletService
from tests.fakes import (
    FixedClock,
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryTransferRepository,
    InMemoryWalletRepository,
    SequentialIdGenerator,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)

ServiceWithUsage = tuple[
    WalletService,
    InMemoryWalletRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryTransferRepository,
]


async def make_service(
    known_currencies: list[Currency] | None = None,
) -> tuple[WalletService, InMemoryWalletRepository, InMemoryCurrencyRepository]:
    service, wallets, currencies, _, _ = await make_service_with_usage(known_currencies)
    return service, wallets, currencies


async def make_service_with_usage(
    known_currencies: list[Currency] | None = None,
) -> ServiceWithUsage:
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(InMemoryCategoryRepository())
    transfers = InMemoryTransferRepository()
    if known_currencies:
        await currencies.upsert_many(known_currencies)
    service = WalletService(wallets, currencies, [transactions, transfers], FixedClock(), SequentialIdGenerator())
    return service, wallets, currencies, transactions, transfers


def make_currency(code: str = "RUB") -> Currency:
    return Currency(id=uuid4(), code=code, name=code, decimal_places=2)


async def test_create_wallet_with_single_currency() -> None:
    currency = make_currency("RUB")
    service, _, _ = await make_service([currency])
    workspace_id = uuid4()

    wallet = await service.create_wallet(workspace_id, name="Наличные", icon="wallet", currency_id=currency.id)

    assert wallet.workspace_id == workspace_id
    assert wallet.name == "Наличные"
    assert wallet.currency_id == currency.id
    assert wallet.created_at is not None


async def test_create_wallet_rejects_unknown_currency() -> None:
    known = make_currency("RUB")
    unknown_id = uuid4()
    service, _, _ = await make_service([known])

    with pytest.raises(ClientError) as exc_info:
        await service.create_wallet(uuid4(), name="Кошелёк", icon="wallet", currency_id=unknown_id)

    assert str(unknown_id) in exc_info.value.message


async def test_get_wallet_unknown_id_raises_not_found() -> None:
    service, _, _ = await make_service()

    with pytest.raises(NotFoundError):
        await service.get_wallet(uuid4(), uuid4())


async def test_get_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=currency.id)

    with pytest.raises(NotFoundError):
        await service.get_wallet(wallet.id, uuid4())


async def test_update_wallet_replaces_fields_and_currency_without_operations() -> None:
    rub, cny = make_currency("RUB"), make_currency("CNY")
    service, _, _ = await make_service([rub, cny])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=rub.id)

    updated = await service.update_wallet(wallet.id, owner, name="Новое имя", icon="banknote", currency_id=cny.id)

    assert updated.name == "Новое имя"
    assert updated.icon == "banknote"
    assert updated.currency_id == cny.id
    assert updated.updated_at is not None


async def test_update_wallet_rejects_unknown_currency() -> None:
    rub = make_currency("RUB")
    service, _, _ = await make_service([rub])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=rub.id)
    unknown_id = uuid4()

    with pytest.raises(ClientError) as exc_info:
        await service.update_wallet(wallet.id, owner, name="X", icon="wallet", currency_id=unknown_id)

    assert str(unknown_id) in exc_info.value.message


async def test_update_wallet_rejects_currency_change_with_transactions() -> None:
    rub, cny = make_currency("RUB"), make_currency("CNY")
    service, _, _, transactions, _ = await make_service_with_usage([rub, cny])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=rub.id)
    await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=owner,
            wallet_id=wallet.id,
            category_id=uuid4(),
            legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("1")),),
            occurred_at=NOW,
            created_at=NOW,
        )
    )

    with pytest.raises(ConflictError):
        await service.update_wallet(wallet.id, owner, name="Кошелёк", icon="wallet", currency_id=cny.id)


async def test_update_wallet_rejects_currency_change_with_transfers() -> None:
    rub, cny = make_currency("RUB"), make_currency("CNY")
    service, _, _, _, transfers = await make_service_with_usage([rub, cny])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=rub.id)
    await transfers.add(
        Transfer(
            id=uuid4(),
            workspace_id=owner,
            from_wallet_id=uuid4(),
            to_wallet_id=wallet.id,
            amount=Decimal("1"),
            occurred_at=NOW,
            created_at=NOW,
        )
    )

    with pytest.raises(ConflictError):
        await service.update_wallet(wallet.id, owner, name="Кошелёк", icon="wallet", currency_id=cny.id)


async def test_update_wallet_with_same_currency_is_allowed_despite_transactions() -> None:
    rub = make_currency("RUB")
    service, _, _, transactions, _ = await make_service_with_usage([rub])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=rub.id)
    await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=owner,
            wallet_id=wallet.id,
            category_id=uuid4(),
            legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("1")),),
            occurred_at=NOW,
            created_at=NOW,
        )
    )

    updated = await service.update_wallet(wallet.id, owner, name="Новое имя", icon="wallet", currency_id=rub.id)

    assert updated.name == "Новое имя"
    assert updated.currency_id == rub.id


async def test_update_wallet_unknown_id_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])

    with pytest.raises(NotFoundError):
        await service.update_wallet(uuid4(), uuid4(), name="X", icon="wallet", currency_id=currency.id)


async def test_update_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=currency.id)

    with pytest.raises(NotFoundError):
        await service.update_wallet(wallet.id, uuid4(), name="X", icon="wallet", currency_id=currency.id)


async def test_delete_wallet_unknown_id_raises_not_found() -> None:
    service, _, _ = await make_service()

    with pytest.raises(NotFoundError):
        await service.delete_wallet(uuid4(), uuid4())


async def test_delete_wallet_belonging_to_another_user_raises_not_found() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=currency.id)

    with pytest.raises(NotFoundError):
        await service.delete_wallet(wallet.id, uuid4())


async def test_delete_wallet_success() -> None:
    currency = make_currency()
    service, wallets, _ = await make_service([currency])
    owner = uuid4()
    wallet = await service.create_wallet(owner, name="Кошелёк", icon="wallet", currency_id=currency.id)

    await service.delete_wallet(wallet.id, owner)

    assert await wallets.get_by_id(wallet.id, owner) is None


async def test_list_wallets_returns_only_given_user_wallets() -> None:
    currency = make_currency()
    service, _, _ = await make_service([currency])
    user_a, user_b = uuid4(), uuid4()
    await service.create_wallet(user_a, name="A1", icon="wallet", currency_id=currency.id)
    await service.create_wallet(user_b, name="B1", icon="wallet", currency_id=currency.id)

    items, total = await service.list_wallets(user_a, limit=20, offset=0)

    assert total == 1
    assert [wallet.name for wallet in items] == ["A1"]
