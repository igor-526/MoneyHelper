from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Wallet
from core.exceptions import ClientError, NotFoundError
from core.services.transaction import TransactionService
from tests.fakes import (
    FixedClock,
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    SequentialIdGenerator,
)


def make_service() -> tuple[
    TransactionService,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    FixedClock,
]:
    categories = InMemoryCategoryRepository()
    transactions = InMemoryTransactionRepository(categories)
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    clock = FixedClock()
    service = TransactionService(transactions, wallets, categories, currencies, clock, SequentialIdGenerator())
    return service, transactions, wallets, categories, currencies, clock


async def make_currency(
    currencies: InMemoryCurrencyRepository, code: str = "RUB", decimal_places: int = 2
) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await currencies.upsert_many([currency])
    return currency


async def make_wallet(wallets: InMemoryWalletRepository, user_id, currency_ids) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        user_id=user_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=tuple(currency_ids),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def make_category(
    categories: InMemoryCategoryRepository, user_id, type: CategoryType = CategoryType.INCOME, name: str | None = None
) -> Category:
    category = Category(
        id=uuid4(),
        user_id=user_id,
        type=type,
        name=name if name is not None else f"Категория {uuid4()}",
        icon="wallet",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await categories.add(category)


async def test_create_transaction_with_explicit_date() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, user_id, [currency.id])
    category = await make_category(categories, user_id, CategoryType.INCOME)
    occurred_at = datetime(2026, 3, 1, tzinfo=UTC)

    transaction = await service.create_transaction(
        user_id,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("100.50"),
        occurred_at=occurred_at,
    )

    assert transaction.wallet_id == wallet.id
    assert transaction.category_id == category.id
    assert transaction.currency_id == currency.id
    assert transaction.amount == Decimal("100.50")
    assert transaction.occurred_at == occurred_at


async def test_create_transaction_without_date_uses_clock_now() -> None:
    service, _, wallets, categories, currencies, clock = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, user_id, [currency.id])
    category = await make_category(categories, user_id)

    transaction = await service.create_transaction(
        user_id,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("10"),
        occurred_at=None,
    )

    assert transaction.occurred_at == clock.now()


async def test_create_transaction_rejects_currency_not_in_wallet() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    user_id = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, user_id, [rub.id])
    category = await make_category(categories, user_id)

    with pytest.raises(ClientError):
        await service.create_transaction(
            user_id,
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=cny.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_amount_exceeding_decimal_places() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies, decimal_places=2)
    wallet = await make_wallet(wallets, user_id, [currency.id])
    category = await make_category(categories, user_id)

    with pytest.raises(ClientError):
        await service.create_transaction(
            user_id,
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("1.005"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_foreign_wallet() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, uuid4())

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            uuid4(),
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_unknown_wallet() -> None:
    service, _, _, categories, currencies, _ = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies)
    category = await make_category(categories, user_id)

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            user_id,
            wallet_id=uuid4(),
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_foreign_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, user_id, [currency.id])
    category = await make_category(categories, uuid4())

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            user_id,
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_unknown_category() -> None:
    service, _, wallets, _, currencies, _ = make_service()
    user_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, user_id, [currency.id])

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            user_id,
            wallet_id=wallet.id,
            category_id=uuid4(),
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_get_transaction_unknown_id_raises_not_found() -> None:
    service, _, _, _, _, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_transaction(uuid4(), uuid4())


async def test_get_transaction_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.get_transaction(transaction.id, uuid4())


async def test_update_transaction_replaces_all_fields() -> None:
    service, _, wallets, categories, currencies, clock = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, owner, [rub.id, cny.id])
    category_a = await make_category(categories, owner, CategoryType.INCOME)
    category_b = await make_category(categories, owner, CategoryType.EXPENSE)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_a.id,
        currency_id=rub.id,
        amount=Decimal("10"),
        occurred_at=None,
    )
    clock.advance(timedelta(days=1))
    new_occurred_at = datetime(2026, 5, 1, tzinfo=UTC)

    updated = await service.update_transaction(
        transaction.id,
        owner,
        wallet_id=wallet.id,
        category_id=category_b.id,
        currency_id=cny.id,
        amount=Decimal("20"),
        occurred_at=new_occurred_at,
    )

    assert updated.category_id == category_b.id
    assert updated.currency_id == cny.id
    assert updated.amount == Decimal("20")
    assert updated.occurred_at == new_occurred_at
    assert updated.updated_at == clock.now()


async def test_update_transaction_unknown_id_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)

    with pytest.raises(NotFoundError):
        await service.update_transaction(
            uuid4(),
            owner,
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("1"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


async def test_update_transaction_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.update_transaction(
            transaction.id,
            uuid4(),
            wallet_id=wallet.id,
            category_id=category.id,
            currency_id=currency.id,
            amount=Decimal("2"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


async def test_delete_transaction_unknown_id_raises_not_found() -> None:
    service, _, _, _, _, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.delete_transaction(uuid4(), uuid4())


async def test_delete_transaction_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.delete_transaction(transaction.id, uuid4())


async def test_delete_transaction_success() -> None:
    service, transactions, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    await service.delete_transaction(transaction.id, owner)

    assert await transactions.get_by_id(transaction.id, owner) is None


async def test_list_transactions_filters_by_wallet() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet_a = await make_wallet(wallets, owner, [currency.id])
    wallet_b = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    await service.create_transaction(
        owner,
        wallet_id=wallet_a.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet_b.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner, wallet_id=wallet_a.id, category_id=None, type=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert items[0].wallet_id == wallet_a.id


async def test_list_transactions_filters_by_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category_a = await make_category(categories, owner)
    category_b = await make_category(categories, owner)
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_a.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_b.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner, wallet_id=None, category_id=category_a.id, type=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert items[0].category_id == category_a.id


async def test_list_transactions_filters_by_type() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    income_category = await make_category(categories, owner, CategoryType.INCOME)
    expense_category = await make_category(categories, owner, CategoryType.EXPENSE)
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=income_category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner,
        wallet_id=None,
        category_id=None,
        type=CategoryType.INCOME,
        date_from=None,
        date_to=None,
        limit=20,
        offset=0,
    )

    assert total == 1
    assert items[0].category_id == income_category.id


async def test_list_transactions_filters_by_date_range() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    category = await make_category(categories, owner)
    early = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    items, total = await service.list_transactions(
        owner,
        wallet_id=None,
        category_id=None,
        type=None,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
        limit=20,
        offset=0,
    )

    assert total == 1
    assert items[0].id == early.id


async def test_list_transactions_rejects_date_from_after_date_to() -> None:
    service, _, _, _, _, _ = make_service()

    with pytest.raises(ClientError):
        await service.list_transactions(
            uuid4(),
            wallet_id=None,
            category_id=None,
            type=None,
            date_from=datetime(2026, 2, 1, tzinfo=UTC),
            date_to=datetime(2026, 1, 1, tzinfo=UTC),
            limit=20,
            offset=0,
        )


async def test_get_wallet_balances_zero_without_transactions() -> None:
    service, _, wallets, _, currencies, _ = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, owner, [rub.id, cny.id])

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(rub.id, Decimal("0")), (cny.id, Decimal("0"))]


async def test_get_wallet_balances_computes_income_minus_expense() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])
    income = await make_category(categories, owner, CategoryType.INCOME)
    expense = await make_category(categories, owner, CategoryType.EXPENSE)
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=income.id,
        currency_id=currency.id,
        amount=Decimal("100"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=expense.id,
        currency_id=currency.id,
        amount=Decimal("30"),
        occurred_at=None,
    )

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(currency.id, Decimal("70"))]


async def test_get_wallet_balances_separates_currencies() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, owner, [rub.id, cny.id])
    income = await make_category(categories, owner, CategoryType.INCOME)
    await service.create_transaction(
        owner, wallet_id=wallet.id, category_id=income.id, currency_id=rub.id, amount=Decimal("100"), occurred_at=None
    )
    await service.create_transaction(
        owner, wallet_id=wallet.id, category_id=income.id, currency_id=cny.id, amount=Decimal("50"), occurred_at=None
    )

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(rub.id, Decimal("100")), (cny.id, Decimal("50"))]


async def test_get_wallet_balances_unknown_wallet_raises_not_found() -> None:
    service, _, _, _, _, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_wallet_balances(uuid4(), uuid4())


async def test_get_wallet_balances_foreign_wallet_raises_not_found() -> None:
    service, _, wallets, _, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, [currency.id])

    with pytest.raises(NotFoundError):
        await service.get_wallet_balances(wallet.id, uuid4())
