from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, Transaction, User, Wallet
from models import categories as categories_table
from models import currencies as currencies_table
from models import transaction_legs as transaction_legs_table
from models import transactions as transactions_table
from models import wallets as wallets_table
from repositories.category import CategoryRepository
from repositories.currency import CurrencyRepository
from repositories.transaction import TransactionRepository
from repositories.user import UserRepository
from repositories.wallet import WalletRepository

pytestmark = pytest.mark.infrastructure

DEFAULT_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


async def make_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        password_hash="hashed:password",
        token_version=0,
        created_at=DEFAULT_CREATED_AT,
    )
    await UserRepository(db_session).add(user)
    await db_session.flush()
    return user


async def make_currency(db_session: AsyncSession, code: str = "RUB", decimal_places: int = 2) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await CurrencyRepository(db_session).upsert_many([currency])
    await db_session.flush()
    return currency


async def make_wallet(db_session: AsyncSession, user_id: UUID, currency_ids: tuple[UUID, ...]) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        user_id=user_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=currency_ids,
        created_at=DEFAULT_CREATED_AT,
    )
    added = await WalletRepository(db_session).add(wallet)
    await db_session.flush()
    return added


async def make_category(
    db_session: AsyncSession, user_id: UUID, type: CategoryType = CategoryType.INCOME, name: str | None = None
) -> Category:
    category = Category(
        id=uuid4(),
        user_id=user_id,
        type=type,
        name=name if name is not None else f"Категория {uuid4()}",
        icon="wallet",
        created_at=DEFAULT_CREATED_AT,
    )
    added = await CategoryRepository(db_session).add(category)
    await db_session.flush()
    return added


def make_transaction(
    user_id: UUID,
    wallet_id: UUID,
    category_id: UUID,
    currency_id: UUID,
    *,
    amount: Decimal = Decimal("100.00"),
    occurred_at: datetime = DEFAULT_CREATED_AT,
) -> Transaction:
    return Transaction(
        id=uuid4(),
        user_id=user_id,
        wallet_id=wallet_id,
        category_id=category_id,
        currency_id=currency_id,
        amount=amount,
        occurred_at=occurred_at,
        created_at=DEFAULT_CREATED_AT,
    )


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, currency.id)

    added = await repo.add(transaction)
    await db_session.flush()

    assert added.amount == Decimal("100.00")
    fetched = await repo.get_by_id(transaction.id, user.id)
    assert fetched is not None
    assert fetched.wallet_id == wallet.id
    assert fetched.category_id == category.id
    assert fetched.currency_id == currency.id
    assert fetched.amount == Decimal("100.00")


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = TransactionRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_get_by_id_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, (currency.id,))
    category = await make_category(db_session, owner.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(owner.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    assert await repo.get_by_id(transaction.id, other.id) is None


async def test_list_and_count_filter_by_wallet(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet_a.id, category.id, currency.id))
    await repo.add(make_transaction(user.id, wallet_b.id, category.id, currency.id))
    await db_session.flush()

    items = await repo.list(
        user.id, wallet_id=wallet_a.id, category_id=None, type=None, date_from=None, date_to=None, limit=20, offset=0
    )
    count = await repo.count(user.id, wallet_id=wallet_a.id, category_id=None, type=None, date_from=None, date_to=None)

    assert len(items) == 1
    assert items[0].wallet_id == wallet_a.id
    assert count == 1


async def test_list_and_count_filter_by_category(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category_a = await make_category(db_session, user.id)
    category_b = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category_a.id, currency.id))
    await repo.add(make_transaction(user.id, wallet.id, category_b.id, currency.id))
    await db_session.flush()

    items = await repo.list(
        user.id, wallet_id=None, category_id=category_a.id, type=None, date_from=None, date_to=None, limit=20, offset=0
    )
    count = await repo.count(
        user.id, wallet_id=None, category_id=category_a.id, type=None, date_from=None, date_to=None
    )

    assert len(items) == 1
    assert items[0].category_id == category_a.id
    assert count == 1


async def test_list_and_count_filter_by_type(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    income = await make_category(db_session, user.id, CategoryType.INCOME)
    expense = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, income.id, currency.id))
    await repo.add(make_transaction(user.id, wallet.id, expense.id, currency.id))
    await db_session.flush()

    items = await repo.list(
        user.id,
        wallet_id=None,
        category_id=None,
        type=CategoryType.INCOME,
        date_from=None,
        date_to=None,
        limit=20,
        offset=0,
    )
    count = await repo.count(
        user.id, wallet_id=None, category_id=None, type=CategoryType.INCOME, date_from=None, date_to=None
    )

    assert len(items) == 1
    assert items[0].category_id == income.id
    assert count == 1


async def test_list_and_count_filter_by_date_range(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    early = make_transaction(
        user.id, wallet.id, category.id, currency.id, occurred_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    late = make_transaction(user.id, wallet.id, category.id, currency.id, occurred_at=datetime(2026, 6, 1, tzinfo=UTC))
    await repo.add(early)
    await repo.add(late)
    await db_session.flush()

    items = await repo.list(
        user.id,
        wallet_id=None,
        category_id=None,
        type=None,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
        limit=20,
        offset=0,
    )
    count = await repo.count(
        user.id,
        wallet_id=None,
        category_id=None,
        type=None,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
    )

    assert [item.id for item in items] == [early.id]
    assert count == 1


async def test_list_combines_filters(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    income = await make_category(db_session, user.id, CategoryType.INCOME)
    expense = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    matching = make_transaction(
        user.id, wallet.id, income.id, currency.id, occurred_at=datetime(2026, 3, 1, tzinfo=UTC)
    )
    await repo.add(matching)
    await repo.add(
        make_transaction(user.id, wallet.id, expense.id, currency.id, occurred_at=datetime(2026, 3, 1, tzinfo=UTC))
    )
    await db_session.flush()

    items = await repo.list(
        user.id,
        wallet_id=wallet.id,
        category_id=income.id,
        type=CategoryType.INCOME,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 12, 1, tzinfo=UTC),
        limit=20,
        offset=0,
    )

    assert [item.id for item in items] == [matching.id]


async def test_list_is_sorted_by_occurred_at_desc_then_id_desc(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 2, 1, tzinfo=UTC)
    first = make_transaction(user.id, wallet.id, category.id, currency.id, occurred_at=later)
    second = make_transaction(user.id, wallet.id, category.id, currency.id, occurred_at=same_moment)
    third = make_transaction(user.id, wallet.id, category.id, currency.id, occurred_at=same_moment)
    for transaction in (second, third, first):
        await repo.add(transaction)
    await db_session.flush()

    items = await repo.list(
        user.id, wallet_id=None, category_id=None, type=None, date_from=None, date_to=None, limit=20, offset=0
    )

    same_moment_ids_desc = sorted([second.id, third.id], reverse=True)
    assert [item.id for item in items] == [first.id, *same_moment_ids_desc]


async def test_update_replaces_all_fields(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, (rub.id, cny.id))
    category_a = await make_category(db_session, user.id, CategoryType.INCOME)
    category_b = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category_a.id, rub.id, amount=Decimal("10.00"))
    await repo.add(transaction)
    await db_session.flush()

    updated = await repo.update(
        transaction.id,
        user.id,
        wallet_id=wallet.id,
        category_id=category_b.id,
        currency_id=cny.id,
        amount=Decimal("20.00"),
        occurred_at=datetime(2026, 5, 1, tzinfo=UTC),
        now=datetime(2026, 5, 2, tzinfo=UTC),
    )
    await db_session.flush()

    assert updated is not None
    assert updated.category_id == category_b.id
    assert updated.currency_id == cny.id
    assert updated.amount == Decimal("20.00")
    assert updated.occurred_at == datetime(2026, 5, 1, tzinfo=UTC)
    assert updated.updated_at == datetime(2026, 5, 2, tzinfo=UTC)


async def test_update_unknown_returns_none(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)

    result = await repo.update(
        uuid4(),
        user.id,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=DEFAULT_CREATED_AT,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None


async def test_update_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, (currency.id,))
    category = await make_category(db_session, owner.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(owner.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    result = await repo.update(
        transaction.id,
        other.id,
        wallet_id=wallet.id,
        category_id=category.id,
        currency_id=currency.id,
        amount=Decimal("999"),
        occurred_at=DEFAULT_CREATED_AT,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None
    unchanged = await repo.get_by_id(transaction.id, owner.id)
    assert unchanged is not None
    assert unchanged.amount == Decimal("100.00")


async def test_delete_success(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    deleted = await repo.delete(transaction.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(transaction.id, user.id) is None


async def test_delete_with_foreign_user_id_returns_false(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, (currency.id,))
    category = await make_category(db_session, owner.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(owner.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    deleted = await repo.delete(transaction.id, other.id)

    assert deleted is False
    assert await repo.get_by_id(transaction.id, owner.id) is not None


async def test_delete_unknown_returns_false(db_session: AsyncSession) -> None:
    repo = TransactionRepository(db_session)

    assert await repo.delete(uuid4(), uuid4()) is False


async def test_deleting_transaction_cascades_to_transaction_legs(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    await repo.delete(transaction.id, user.id)
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(transaction_legs_table).where(transaction_legs_table.c.transaction_id == transaction.id)
        )
    ).all()
    assert rows == []


async def test_inserting_leg_with_unknown_wallet_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, uuid4(), category.id, currency.id)

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_inserting_leg_with_unknown_category_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, uuid4(), currency.id)

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_inserting_leg_with_unknown_currency_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, uuid4())

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_deleting_referenced_wallet_is_restricted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(wallets_table.delete().where(wallets_table.c.id == wallet.id))


async def test_deleting_referenced_category_is_restricted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(categories_table.delete().where(categories_table.c.id == category.id))


async def test_deleting_referenced_currency_is_restricted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(currencies_table.delete().where(currencies_table.c.id == currency.id))


async def test_check_constraint_rejects_nonpositive_amount(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    category = await make_category(db_session, user.id)
    transaction_id = uuid4()
    await db_session.execute(
        insert(transactions_table).values(
            id=transaction_id,
            user_id=user.id,
            wallet_id=wallet.id,
            category_id=category.id,
            occurred_at=DEFAULT_CREATED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.execute(
            insert(transaction_legs_table).values(
                transaction_id=transaction_id, currency_id=currency.id, amount=Decimal("0")
            )
        )


async def test_balances_sum_income_and_expense_per_currency(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, (rub.id, cny.id))
    income = await make_category(db_session, user.id, CategoryType.INCOME)
    expense = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, income.id, rub.id, amount=Decimal("100.00")))
    await repo.add(make_transaction(user.id, wallet.id, expense.id, rub.id, amount=Decimal("30.00")))
    await repo.add(make_transaction(user.id, wallet.id, income.id, cny.id, amount=Decimal("50.00")))
    await db_session.flush()

    balances = await repo.balances(wallet.id, user.id)

    assert balances[rub.id] == Decimal("70.00")
    assert balances[cny.id] == Decimal("50.00")


async def test_balances_excludes_other_wallets_and_users(db_session: AsyncSession) -> None:
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user_a.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user_a.id, (currency.id,))
    category_a = await make_category(db_session, user_a.id, CategoryType.INCOME)
    category_b = await make_category(db_session, user_b.id, CategoryType.INCOME)
    wallet_b_user_b = await make_wallet(db_session, user_b.id, (currency.id,))
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user_a.id, wallet_a.id, category_a.id, currency.id, amount=Decimal("10.00")))
    await repo.add(make_transaction(user_a.id, wallet_b.id, category_a.id, currency.id, amount=Decimal("20.00")))
    await repo.add(
        make_transaction(user_b.id, wallet_b_user_b.id, category_b.id, currency.id, amount=Decimal("999.00"))
    )
    await db_session.flush()

    balances = await repo.balances(wallet_a.id, user_a.id)

    assert balances == {currency.id: Decimal("10.00")}


async def test_balances_empty_for_wallet_without_transactions(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransactionRepository(db_session)

    balances = await repo.balances(wallet.id, user.id)

    assert balances == {}
