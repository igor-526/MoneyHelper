from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Wallet
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


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id, currency_id) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_id=currency_id,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def make_category(
    categories: InMemoryCategoryRepository,
    workspace_id,
    type: CategoryType = CategoryType.EXPENSE,
    name: str | None = None,
) -> Category:
    category = Category(
        id=uuid4(),
        workspace_id=workspace_id,
        type=type,
        name=name if name is not None else f"Категория {uuid4()}",
        icon="wallet",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await categories.add(category)


async def test_create_transaction_with_explicit_date() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id, CategoryType.EXPENSE)
    occurred_at = datetime(2026, 3, 1, tzinfo=UTC)

    transaction = await service.create_transaction(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("100.50"),
        occurred_at=occurred_at,
    )

    assert transaction.wallet_id == wallet.id
    assert transaction.category_id == category.id
    assert transaction.legs == (TransactionLeg(currency_id=currency.id, amount=Decimal("100.50")),)
    assert transaction.occurred_at == occurred_at


async def test_create_transaction_without_date_uses_clock_now() -> None:
    service, _, wallets, categories, currencies, clock = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id)

    transaction = await service.create_transaction(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
    )

    assert transaction.occurred_at == clock.now()


async def test_create_transaction_uses_wallet_currency() -> None:
    service, repository, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, workspace_id, cny.id)
    category = await make_category(categories, workspace_id)

    transaction = await service.create_transaction(
        workspace_id, wallet_id=wallet.id, category_id=category.id, amount=Decimal("5"), occurred_at=None
    )

    assert transaction.legs == (TransactionLeg(currency_id=cny.id, amount=Decimal("5")),)
    stored = await repository.get_by_id(transaction.id, workspace_id)
    assert stored is not None
    assert stored.legs == transaction.legs


async def test_update_transaction_uses_new_wallet_currency() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    rub_wallet = await make_wallet(wallets, workspace_id, rub.id)
    cny_wallet = await make_wallet(wallets, workspace_id, cny.id)
    category = await make_category(categories, workspace_id)
    transaction = await service.create_transaction(
        workspace_id, wallet_id=rub_wallet.id, category_id=category.id, amount=Decimal("5"), occurred_at=None
    )

    updated = await service.update_transaction(
        transaction.id,
        workspace_id,
        wallet_id=cny_wallet.id,
        category_id=category.id,
        amount=Decimal("7"),
        occurred_at=None,
    )

    assert updated.legs == (TransactionLeg(currency_id=cny.id, amount=Decimal("7")),)


async def test_create_transaction_rejects_amount_exceeding_decimal_places() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies, decimal_places=2)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id)

    with pytest.raises(ClientError):
        await service.create_transaction(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            amount=Decimal("1.005"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_foreign_wallet() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, uuid4())

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            uuid4(),
            wallet_id=wallet.id,
            category_id=category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_unknown_wallet() -> None:
    service, _, _, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    await make_currency(currencies)
    category = await make_category(categories, workspace_id)

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            workspace_id,
            wallet_id=uuid4(),
            category_id=category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_foreign_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, uuid4())

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_create_transaction_rejects_unknown_category() -> None:
    service, _, wallets, _, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)

    with pytest.raises(NotFoundError):
        await service.create_transaction(
            workspace_id,
            wallet_id=wallet.id,
            category_id=uuid4(),
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
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.get_transaction(transaction.id, uuid4())


async def test_update_transaction_replaces_all_fields() -> None:
    service, _, wallets, categories, currencies, clock = make_service()
    owner = uuid4()
    rub = await make_currency(currencies, "RUB")
    wallet = await make_wallet(wallets, owner, rub.id)
    category_a = await make_category(categories, owner, CategoryType.EXPENSE)
    category_b = await make_category(categories, owner, CategoryType.EXPENSE)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_a.id,
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
        amount=Decimal("20"),
        occurred_at=new_occurred_at,
    )

    assert updated.category_id == category_b.id
    assert updated.legs == (TransactionLeg(currency_id=rub.id, amount=Decimal("20")),)
    assert updated.occurred_at == new_occurred_at
    assert updated.updated_at == clock.now()


async def test_update_transaction_unknown_id_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)

    with pytest.raises(NotFoundError):
        await service.update_transaction(
            uuid4(),
            owner,
            wallet_id=wallet.id,
            category_id=category.id,
            amount=Decimal("1"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


async def test_update_transaction_belonging_to_another_user_raises_not_found() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.update_transaction(
            transaction.id,
            uuid4(),
            wallet_id=wallet.id,
            category_id=category.id,
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
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(NotFoundError):
        await service.delete_transaction(transaction.id, uuid4())


async def test_delete_transaction_success() -> None:
    service, transactions, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    await service.delete_transaction(transaction.id, owner)

    assert await transactions.get_by_id(transaction.id, owner) is None


async def test_list_transactions_filters_by_wallet() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet_a = await make_wallet(wallets, owner, currency.id)
    wallet_b = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    await service.create_transaction(
        owner,
        wallet_id=wallet_a.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet_b.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner, wallet_id=wallet_a.id, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert items[0].wallet_id == wallet_a.id


async def test_list_transactions_filters_by_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category_a = await make_category(categories, owner)
    category_b = await make_category(categories, owner)
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_a.id,
        amount=Decimal("1"),
        occurred_at=None,
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category_b.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner, wallet_id=None, category_id=category_a.id, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert items[0].category_id == category_a.id


async def test_list_transactions_returns_only_expenses() -> None:
    service, transactions, wallets, categories, currencies, clock = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    income_category = await make_category(categories, owner, CategoryType.INCOME)
    expense_category = await make_category(categories, owner, CategoryType.EXPENSE)
    await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=owner,
            wallet_id=wallet.id,
            category_id=income_category.id,
            legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("1")),),
            occurred_at=clock.now(),
            created_at=clock.now(),
        )
    )
    expense = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    items, total = await service.list_transactions(
        owner, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert [item.id for item in items] == [expense.id]


async def test_create_transaction_rejects_income_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner, CategoryType.INCOME)

    with pytest.raises(ClientError):
        await service.create_transaction(
            owner,
            wallet_id=wallet.id,
            category_id=category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_update_transaction_rejects_income_category() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    expense_category = await make_category(categories, owner, CategoryType.EXPENSE)
    income_category = await make_category(categories, owner, CategoryType.INCOME)
    transaction = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount=Decimal("1"),
        occurred_at=None,
    )

    with pytest.raises(ClientError):
        await service.update_transaction(
            transaction.id,
            owner,
            wallet_id=wallet.id,
            category_id=income_category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )


async def test_topup_is_not_accessible_as_transaction() -> None:
    service, transactions, wallets, categories, currencies, clock = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    income_category = await make_category(categories, owner, CategoryType.INCOME)
    topup = await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=owner,
            wallet_id=wallet.id,
            category_id=income_category.id,
            legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("1")),),
            occurred_at=clock.now(),
            created_at=clock.now(),
        )
    )

    with pytest.raises(NotFoundError):
        await service.get_transaction(topup.id, owner)
    with pytest.raises(NotFoundError):
        await service.update_transaction(
            topup.id,
            owner,
            wallet_id=wallet.id,
            category_id=income_category.id,
            amount=Decimal("1"),
            occurred_at=None,
        )
    with pytest.raises(NotFoundError):
        await service.delete_transaction(topup.id, owner)
    assert await transactions.get_by_id(topup.id, owner) is not None


async def test_list_transactions_filters_by_date_range() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    owner = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, owner, currency.id)
    category = await make_category(categories, owner)
    early = await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await service.create_transaction(
        owner,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("1"),
        occurred_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    items, total = await service.list_transactions(
        owner,
        wallet_id=None,
        category_id=None,
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
            date_from=datetime(2026, 2, 1, tzinfo=UTC),
            date_to=datetime(2026, 1, 1, tzinfo=UTC),
            limit=20,
            offset=0,
        )


async def test_create_transaction_with_comment() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id, CategoryType.EXPENSE)

    transaction = await service.create_transaction(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
        comment="Серый рюкзак",
    )

    assert transaction.comment == "Серый рюкзак"


async def test_create_transaction_without_comment_defaults_to_none() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id, CategoryType.EXPENSE)

    transaction = await service.create_transaction(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
    )

    assert transaction.comment is None


async def test_update_transaction_sets_and_clears_comment() -> None:
    service, _, wallets, categories, currencies, _ = make_service()
    workspace_id = uuid4()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id, CategoryType.EXPENSE)
    transaction = await service.create_transaction(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
        comment="Исходный комментарий",
    )

    with_new_comment = await service.update_transaction(
        transaction.id,
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
        comment="Новый комментарий",
    )
    assert with_new_comment.comment == "Новый комментарий"

    cleared = await service.update_transaction(
        transaction.id,
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=Decimal("10"),
        occurred_at=None,
    )
    assert cleared.comment is None
