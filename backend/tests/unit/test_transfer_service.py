from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from core.entities import Currency, Wallet
from core.exceptions import ClientError, NotFoundError
from core.services.transfer import TransferService
from tests.fakes import (
    FixedClock,
    InMemoryCurrencyRepository,
    InMemoryTransferRepository,
    InMemoryWalletRepository,
    SequentialIdGenerator,
)


def make_service() -> tuple[
    TransferService, InMemoryTransferRepository, InMemoryWalletRepository, InMemoryCurrencyRepository, FixedClock
]:
    transfers = InMemoryTransferRepository()
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    clock = FixedClock()
    service = TransferService(transfers, wallets, currencies, clock, SequentialIdGenerator())
    return service, transfers, wallets, currencies, clock


async def make_currency(
    currencies: InMemoryCurrencyRepository, code: str = "RUB", decimal_places: int = 2
) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await currencies.upsert_many([currency])
    return currency


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id, currency_ids) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=tuple(currency_ids),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def test_create_transfer_with_explicit_date() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])
    occurred_at = datetime(2026, 3, 1, tzinfo=UTC)

    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("100"),
        occurred_at=occurred_at,
    )

    assert transfer.from_wallet_id == from_wallet.id
    assert transfer.to_wallet_id == to_wallet.id
    assert transfer.currency_id == currency.id
    assert transfer.amount == Decimal("100")
    assert transfer.occurred_at == occurred_at


async def test_create_transfer_without_date_uses_clock_now() -> None:
    service, _, wallets, currencies, clock = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])

    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("100"),
        occurred_at=None,
    )

    assert transfer.occurred_at == clock.now()


async def test_create_transfer_rejects_same_wallet() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(ClientError):
        await service.create_transfer(
            owner,
            from_wallet_id=wallet.id,
            to_wallet_id=wallet.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_no_shared_currency() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    from_wallet = await make_wallet(wallets, owner, [rub.id])
    to_wallet = await make_wallet(wallets, owner, [cny.id])

    with pytest.raises(ClientError):
        await service.create_transfer(
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=rub.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_currency_not_in_one_of_wallets_despite_shared_currency() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    from_wallet = await make_wallet(wallets, owner, [rub.id, cny.id])
    to_wallet = await make_wallet(wallets, owner, [rub.id])

    with pytest.raises(ClientError):
        await service.create_transfer(
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=cny.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_nonpositive_amount() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(ClientError):
        await service.create_transfer(
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("0"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_amount_exceeding_decimal_places() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies, decimal_places=2)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(ClientError):
        await service.create_transfer(
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("1.005"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_foreign_from_wallet() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, uuid4(), [currency.id])

    with pytest.raises(NotFoundError):
        await service.create_transfer(
            uuid4(),
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_unknown_from_wallet() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    to_wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(NotFoundError):
        await service.create_transfer(
            owner,
            from_wallet_id=uuid4(),
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transfer_rejects_unknown_to_wallet() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(NotFoundError):
        await service.create_transfer(
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=uuid4(),
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_get_transfer_unknown_id_raises_not_found() -> None:
    service, _, _, _, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_transfer(uuid4(), uuid4())


async def test_get_transfer_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])
    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.get_transfer(transfer.id, uuid4())


async def test_update_transfer_replaces_all_fields() -> None:
    service, _, wallets, currencies, clock = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet_a = await make_wallet(wallets, owner, [currency.id])
    wallet_b = await make_wallet(wallets, owner, [currency.id])
    wallet_c = await make_wallet(wallets, owner, [currency.id])
    transfer = await service.create_transfer(
        owner,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("10"),
        occurred_at=None,
    )
    new_occurred_at = datetime(2026, 5, 1, tzinfo=UTC)

    updated = await service.update_transfer(
        transfer.id,
        owner,
        from_wallet_id=wallet_b.id,
        to_wallet_id=wallet_c.id,
        currency_id=currency.id,
        amount=Decimal("20"),
        occurred_at=new_occurred_at,
    )

    assert updated.from_wallet_id == wallet_b.id
    assert updated.to_wallet_id == wallet_c.id
    assert updated.amount == Decimal("20")
    assert updated.occurred_at == new_occurred_at
    assert updated.updated_at == clock.now()


async def test_update_transfer_unknown_id_raises_not_found() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(NotFoundError):
        await service.update_transfer(
            uuid4(),
            owner,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


async def test_update_transfer_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])
    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.update_transfer(
            transfer.id,
            uuid4(),
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            amount=Decimal("2"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


async def test_delete_transfer_unknown_id_raises_not_found() -> None:
    service, _, _, _, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.delete_transfer(uuid4(), uuid4())


async def test_delete_transfer_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])
    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.delete_transfer(transfer.id, uuid4())


async def test_delete_transfer_success() -> None:
    service, transfers, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, owner, [currency.id])
    to_wallet = await make_wallet(wallets, owner, [currency.id])
    transfer = await service.create_transfer(
        owner,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    await service.delete_transfer(transfer.id, owner)

    assert await transfers.get_by_id(transfer.id, owner) is None


async def test_list_transfers_filters_by_wallet_matches_from_or_to() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet_a = await make_wallet(wallets, owner, [currency.id])
    wallet_b = await make_wallet(wallets, owner, [currency.id])
    wallet_c = await make_wallet(wallets, owner, [currency.id])
    await service.create_transfer(
        owner,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transfer(
        owner,
        from_wallet_id=wallet_b.id,
        to_wallet_id=wallet_c.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transfer(
        owner,
        from_wallet_id=wallet_c.id,
        to_wallet_id=wallet_a.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transfers(
        owner, wallet_id=wallet_b.id, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 2
    assert {(item.from_wallet_id, item.to_wallet_id) for item in items} == {
        (wallet_a.id, wallet_b.id),
        (wallet_b.id, wallet_c.id),
    }


async def test_list_transfers_filters_by_date_range() -> None:
    service, _, wallets, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet_a = await make_wallet(wallets, owner, [currency.id])
    wallet_b = await make_wallet(wallets, owner, [currency.id])
    early = await service.create_transfer(
        owner,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await service.create_transfer(
        owner,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    items, total = await service.list_transfers(
        owner,
        wallet_id=None,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
        limit=20,
        offset=0,
    )

    assert total == 1
    assert items[0].id == early.id


async def test_list_transfers_rejects_date_from_after_date_to() -> None:
    service, _, _, _, _ = make_service()

    with pytest.raises(ClientError):
        await service.list_transfers(
            uuid4(),
            wallet_id=None,
            date_from=datetime(2026, 2, 1, tzinfo=UTC),
            date_to=datetime(2026, 1, 1, tzinfo=UTC),
            limit=20,
            offset=0,
        )
