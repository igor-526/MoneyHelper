from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, User, Wallet, Workspace
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
from repositories.workspace import WorkspaceRepository
from tests.infrastructure.factories import make_workspace_currency

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


async def make_workspace(db_session: AsyncSession, owner: User | None = None) -> Workspace:
    owner = owner if owner is not None else await make_user(db_session)
    currency = await make_workspace_currency(db_session)
    workspace = Workspace(
        id=uuid4(), user_id=owner.id, name="Воркспейс", currency_id=currency.id, created_at=DEFAULT_CREATED_AT
    )
    await WorkspaceRepository(db_session).add(workspace)
    await db_session.flush()
    return workspace


async def make_currency(db_session: AsyncSession, code: str = "RUB", decimal_places: int = 2) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await CurrencyRepository(db_session).upsert_many([currency])
    await db_session.flush()
    return currency


async def make_wallet(db_session: AsyncSession, workspace_id: UUID, currency_id: UUID) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_id=currency_id,
        created_at=DEFAULT_CREATED_AT,
    )
    added = await WalletRepository(db_session).add(wallet)
    await db_session.flush()
    return added


async def make_category(
    db_session: AsyncSession, workspace_id: UUID, type: CategoryType = CategoryType.INCOME, name: str | None = None
) -> Category:
    category = Category(
        id=uuid4(),
        workspace_id=workspace_id,
        type=type,
        name=name if name is not None else f"Категория {uuid4()}",
        icon="wallet",
        created_at=DEFAULT_CREATED_AT,
    )
    added = await CategoryRepository(db_session).add(category)
    await db_session.flush()
    return added


def make_transaction(
    workspace_id: UUID,
    wallet_id: UUID,
    category_id: UUID,
    currency_id: UUID,
    *,
    amount: Decimal = Decimal("100.00"),
    occurred_at: datetime = DEFAULT_CREATED_AT,
) -> Transaction:
    return Transaction(
        id=uuid4(),
        workspace_id=workspace_id,
        wallet_id=wallet_id,
        category_id=category_id,
        legs=(TransactionLeg(currency_id=currency_id, amount=amount),),
        occurred_at=occurred_at,
        created_at=DEFAULT_CREATED_AT,
    )


def make_topup(
    workspace_id: UUID,
    wallet_id: UUID,
    category_id: UUID,
    legs: tuple[TransactionLeg, ...],
    *,
    occurred_at: datetime = DEFAULT_CREATED_AT,
) -> Transaction:
    return Transaction(
        id=uuid4(),
        workspace_id=workspace_id,
        wallet_id=wallet_id,
        category_id=category_id,
        legs=legs,
        occurred_at=occurred_at,
        created_at=DEFAULT_CREATED_AT,
    )


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, currency.id)

    added = await repo.add(transaction)
    await db_session.flush()

    assert added.legs == (TransactionLeg(currency_id=currency.id, amount=Decimal("100.00")),)
    fetched = await repo.get_by_id(transaction.id, user.id)
    assert fetched is not None
    assert fetched.wallet_id == wallet.id
    assert fetched.category_id == category.id
    assert fetched.legs == (TransactionLeg(currency_id=currency.id, amount=Decimal("100.00")),)


async def test_add_and_get_by_id_with_multiple_legs(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    usdt = await make_currency(db_session, "USDT")
    wallet = await make_wallet(db_session, user.id, rub.id)
    category = await make_category(db_session, user.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    # Намеренно вставлены не в алфавитном порядке кода.
    topup = make_topup(
        user.id,
        wallet.id,
        category.id,
        (
            TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
            TransactionLeg(currency_id=usdt.id, amount=Decimal("100.00")),
            TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        ),
    )

    await repo.add(topup)
    await db_session.flush()

    fetched = await repo.get_by_id(topup.id, user.id)
    assert fetched is not None
    assert fetched.legs == (
        TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
        TransactionLeg(currency_id=usdt.id, amount=Decimal("100.00")),
    )


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = TransactionRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_get_by_id_with_foreign_workspace_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, currency.id)
    category = await make_category(db_session, owner.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(owner.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    assert await repo.get_by_id(transaction.id, other.id) is None


async def test_list_and_count_filter_by_wallet(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, currency.id)
    wallet_b = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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


async def test_list_aggregates_legs_for_multiple_transactions_without_n_plus_one(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, rub.id)
    category = await make_category(db_session, user.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    single_leg = make_transaction(user.id, wallet.id, category.id, rub.id, amount=Decimal("50.00"))
    multi_leg = make_topup(
        user.id,
        wallet.id,
        category.id,
        (
            TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
            TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        ),
    )
    await repo.add(single_leg)
    await repo.add(multi_leg)
    await db_session.flush()

    # `_load_legs_map` выполняет один батч-запрос по всем `transaction_id` страницы сразу (см. design.md,
    # раздел 2) — здесь явно проверяется корректность агрегации ног на нескольких операциях с разным их
    # числом, а не количество SQL-запросов напрямую.
    items = await repo.list(
        user.id, wallet_id=None, category_id=None, type=None, date_from=None, date_to=None, limit=20, offset=0
    )

    by_id = {item.id: item for item in items}
    assert by_id[single_leg.id].legs == (TransactionLeg(currency_id=rub.id, amount=Decimal("50.00")),)
    assert by_id[multi_leg.id].legs == (
        TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
    )


async def test_update_replaces_all_fields(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, rub.id)
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
        legs=(TransactionLeg(currency_id=cny.id, amount=Decimal("20.00")),),
        occurred_at=datetime(2026, 5, 1, tzinfo=UTC),
        comment=None,
        now=datetime(2026, 5, 2, tzinfo=UTC),
    )
    await db_session.flush()

    assert updated is not None
    assert updated.category_id == category_b.id
    assert updated.legs == (TransactionLeg(currency_id=cny.id, amount=Decimal("20.00")),)
    assert updated.occurred_at == datetime(2026, 5, 1, tzinfo=UTC)
    assert updated.updated_at == datetime(2026, 5, 2, tzinfo=UTC)


async def test_update_replaces_multiple_legs_with_one(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, rub.id)
    category = await make_category(db_session, user.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    topup = make_topup(
        user.id,
        wallet.id,
        category.id,
        (
            TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
            TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        ),
    )
    await repo.add(topup)
    await db_session.flush()

    updated = await repo.update(
        topup.id,
        user.id,
        wallet_id=wallet.id,
        category_id=category.id,
        legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("1.00")),),
        occurred_at=DEFAULT_CREATED_AT,
        comment=None,
        now=DEFAULT_CREATED_AT,
    )
    await db_session.flush()

    assert updated is not None
    assert updated.legs == (TransactionLeg(currency_id=rub.id, amount=Decimal("1.00")),)


async def test_update_unknown_returns_none(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)

    result = await repo.update(
        uuid4(),
        user.id,
        wallet_id=wallet.id,
        category_id=category.id,
        legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("1")),),
        occurred_at=DEFAULT_CREATED_AT,
        comment=None,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None


async def test_update_with_foreign_workspace_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, currency.id)
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
        legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("999")),),
        occurred_at=DEFAULT_CREATED_AT,
        comment=None,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None
    unchanged = await repo.get_by_id(transaction.id, owner.id)
    assert unchanged is not None
    assert unchanged.legs == (TransactionLeg(currency_id=currency.id, amount=Decimal("100.00")),)


async def test_delete_success(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, currency.id)
    await repo.add(transaction)
    await db_session.flush()

    deleted = await repo.delete(transaction.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(transaction.id, user.id) is None


async def test_delete_with_foreign_workspace_id_returns_false(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, owner.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
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
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, uuid4(), category.id, currency.id)

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_inserting_leg_with_unknown_category_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, uuid4(), currency.id)

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_inserting_leg_with_unknown_currency_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    transaction = make_transaction(user.id, wallet.id, category.id, uuid4())

    with pytest.raises(IntegrityError):
        await repo.add(transaction)


async def test_deleting_referenced_wallet_is_restricted(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(wallets_table.delete().where(wallets_table.c.id == wallet.id))


async def test_deleting_referenced_category_is_restricted(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(categories_table.delete().where(categories_table.c.id == category.id))


async def test_deleting_referenced_currency_is_restricted(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, category.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(currencies_table.delete().where(currencies_table.c.id == currency.id))


async def test_check_constraint_rejects_nonpositive_amount(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id)
    transaction_id = uuid4()
    await db_session.execute(
        insert(transactions_table).values(
            id=transaction_id,
            workspace_id=user.id,
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


async def test_balance_delta_sums_income_and_expense_in_requested_currency(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, rub.id)
    income = await make_category(db_session, user.id, CategoryType.INCOME)
    expense = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user.id, wallet.id, income.id, rub.id, amount=Decimal("100.00")))
    await repo.add(make_transaction(user.id, wallet.id, expense.id, rub.id, amount=Decimal("30.00")))
    await repo.add(make_transaction(user.id, wallet.id, income.id, cny.id, amount=Decimal("50.00")))
    await db_session.flush()

    assert await repo.balance_delta(wallet.id, user.id, rub.id) == Decimal("70.00")
    assert await repo.balance_delta(wallet.id, user.id, cny.id) == Decimal("50.00")


async def test_balance_delta_excludes_other_wallets_and_users(db_session: AsyncSession) -> None:
    user_a = await make_workspace(db_session)
    user_b = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user_a.id, currency.id)
    wallet_b = await make_wallet(db_session, user_a.id, currency.id)
    category_a = await make_category(db_session, user_a.id, CategoryType.INCOME)
    category_b = await make_category(db_session, user_b.id, CategoryType.INCOME)
    wallet_b_user_b = await make_wallet(db_session, user_b.id, currency.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(user_a.id, wallet_a.id, category_a.id, currency.id, amount=Decimal("10.00")))
    await repo.add(make_transaction(user_a.id, wallet_b.id, category_a.id, currency.id, amount=Decimal("20.00")))
    await repo.add(
        make_transaction(user_b.id, wallet_b_user_b.id, category_b.id, currency.id, amount=Decimal("999.00"))
    )
    await db_session.flush()

    balance = await repo.balance_delta(wallet_a.id, user_a.id, currency.id)

    assert balance == Decimal("10.00")


async def test_balance_delta_zero_for_wallet_without_transactions(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    repo = TransactionRepository(db_session)

    balance = await repo.balance_delta(wallet.id, user.id, currency.id)

    assert balance == Decimal("0")


async def test_list_legs_for_analytics_filters_by_date_range(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, currency.id)
    category = await make_category(db_session, user.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    early = make_transaction(
        user.id, wallet.id, category.id, currency.id, occurred_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    late = make_transaction(user.id, wallet.id, category.id, currency.id, occurred_at=datetime(2026, 6, 1, tzinfo=UTC))
    await repo.add(early)
    await repo.add(late)
    await db_session.flush()

    legs = await repo.list_legs_for_analytics(
        user.id,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert len(legs) == 1
    assert legs[0].wallet_id == wallet.id
    assert legs[0].category_id == category.id
    assert legs[0].currency_id == currency.id
    assert legs[0].amount == Decimal("100.00")
    assert legs[0].category_type == CategoryType.INCOME


async def test_list_legs_for_analytics_filters_by_wallet_category_currency_type(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet_a = await make_wallet(db_session, user.id, rub.id)
    wallet_b = await make_wallet(db_session, user.id, rub.id)
    income = await make_category(db_session, user.id, CategoryType.INCOME)
    expense = await make_category(db_session, user.id, CategoryType.EXPENSE)
    repo = TransactionRepository(db_session)
    matching = make_transaction(user.id, wallet_a.id, income.id, rub.id, amount=Decimal("10.00"))
    await repo.add(matching)
    await repo.add(make_transaction(user.id, wallet_a.id, income.id, cny.id, amount=Decimal("20.00")))
    await repo.add(make_transaction(user.id, wallet_a.id, expense.id, rub.id, amount=Decimal("30.00")))
    await repo.add(make_transaction(user.id, wallet_b.id, income.id, rub.id, amount=Decimal("40.00")))
    await db_session.flush()

    legs = await repo.list_legs_for_analytics(
        user.id,
        date_from=datetime(2025, 1, 1, tzinfo=UTC),
        date_to=datetime(2027, 1, 1, tzinfo=UTC),
        wallet_id=wallet_a.id,
        category_id=income.id,
        currency_id=rub.id,
        type=CategoryType.INCOME,
    )

    assert len(legs) == 1
    assert legs[0].amount == Decimal("10.00")


async def test_list_legs_for_analytics_isolated_by_user(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_owner = await make_wallet(db_session, owner.id, currency.id)
    wallet_other = await make_wallet(db_session, other.id, currency.id)
    category_owner = await make_category(db_session, owner.id, CategoryType.INCOME)
    category_other = await make_category(db_session, other.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    await repo.add(make_transaction(owner.id, wallet_owner.id, category_owner.id, currency.id, amount=Decimal("5.00")))
    await repo.add(
        make_transaction(other.id, wallet_other.id, category_other.id, currency.id, amount=Decimal("999.00"))
    )
    await db_session.flush()

    legs = await repo.list_legs_for_analytics(
        owner.id,
        date_from=datetime(2025, 1, 1, tzinfo=UTC),
        date_to=datetime(2027, 1, 1, tzinfo=UTC),
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert len(legs) == 1
    assert legs[0].amount == Decimal("5.00")


async def test_list_legs_for_analytics_includes_all_legs_of_multi_leg_transaction(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, user.id, rub.id)
    category = await make_category(db_session, user.id, CategoryType.INCOME)
    repo = TransactionRepository(db_session)
    await repo.add(
        make_topup(
            user.id,
            wallet.id,
            category.id,
            (
                TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
                TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
            ),
        )
    )
    await db_session.flush()

    legs = await repo.list_legs_for_analytics(
        user.id,
        date_from=datetime(2025, 1, 1, tzinfo=UTC),
        date_to=datetime(2027, 1, 1, tzinfo=UTC),
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    amounts_by_currency = {leg.currency_id: leg.amount for leg in legs}
    assert amounts_by_currency == {rub.id: Decimal("10000.00"), cny.id: Decimal("780.00")}


async def make_topup_environment(
    db_session: AsyncSession, workspace: Workspace
) -> tuple[Currency, Currency, Wallet, Category, Category]:
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    wallet = await make_wallet(db_session, workspace.id, cny.id)
    income = await make_category(db_session, workspace.id, CategoryType.INCOME)
    expense = await make_category(db_session, workspace.id, CategoryType.EXPENSE)
    return rub, cny, wallet, income, expense


def make_cross_topup(
    workspace_id: UUID,
    wallet_id: UUID,
    category_id: UUID,
    rub: Currency,
    cny: Currency,
    *,
    occurred_at: datetime = DEFAULT_CREATED_AT,
) -> Transaction:
    return make_topup(
        workspace_id,
        wallet_id,
        category_id,
        (
            TransactionLeg(currency_id=rub.id, amount=Decimal("10000.00")),
            TransactionLeg(currency_id=cny.id, amount=Decimal("780.00")),
        ),
        occurred_at=occurred_at,
    )


async def test_list_topup_legs_for_rates_selects_by_income_category_not_leg_count(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    rub, cny, wallet, income, expense = await make_topup_environment(db_session, workspace)
    repo = TransactionRepository(db_session)
    same_currency_topup = make_transaction(workspace.id, wallet.id, income.id, cny.id, amount=Decimal("50.00"))
    await repo.add(same_currency_topup)
    await repo.add(make_transaction(workspace.id, wallet.id, expense.id, cny.id, amount=Decimal("7.00")))
    cross_topup = make_cross_topup(workspace.id, wallet.id, income.id, rub, cny)
    await repo.add(cross_topup)
    await db_session.flush()

    legs = await repo.list_topup_legs_for_rates(workspace.id, wallet_id=None, date_from=None, date_to=None)

    assert {leg.transaction_id for leg in legs} == {same_currency_topup.id, cross_topup.id}
    cross_amounts = {leg.currency_id: leg.amount for leg in legs if leg.transaction_id == cross_topup.id}
    assert cross_amounts == {rub.id: Decimal("10000.00"), cny.id: Decimal("780.00")}


async def test_list_topup_legs_for_rates_ignores_multi_leg_expense(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    rub, cny, wallet, _, expense = await make_topup_environment(db_session, workspace)
    repo = TransactionRepository(db_session)
    await repo.add(make_cross_topup(workspace.id, wallet.id, expense.id, rub, cny))
    await db_session.flush()

    legs = await repo.list_topup_legs_for_rates(workspace.id, wallet_id=None, date_from=None, date_to=None)

    assert legs == []


async def test_list_topup_legs_for_rates_filters_by_date_range(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    rub, cny, wallet, income, _ = await make_topup_environment(db_session, workspace)
    repo = TransactionRepository(db_session)
    june = datetime(2026, 6, 1, tzinfo=UTC)
    await repo.add(make_cross_topup(workspace.id, wallet.id, income.id, rub, cny, occurred_at=june))
    await db_session.flush()

    early, late = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 12, 1, tzinfo=UTC)
    outside = await repo.list_topup_legs_for_rates(
        workspace.id, wallet_id=None, date_from=datetime(2025, 1, 1, tzinfo=UTC), date_to=early
    )
    inside = await repo.list_topup_legs_for_rates(workspace.id, wallet_id=None, date_from=early, date_to=late)

    assert outside == []
    assert len(inside) == 2


async def test_list_topup_legs_for_rates_filters_by_wallet(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    rub, cny, wallet, income, _ = await make_topup_environment(db_session, workspace)
    other_wallet = await make_wallet(db_session, workspace.id, cny.id)
    repo = TransactionRepository(db_session)
    await repo.add(make_cross_topup(workspace.id, wallet.id, income.id, rub, cny))
    await repo.add(make_cross_topup(workspace.id, other_wallet.id, income.id, rub, cny))
    await db_session.flush()

    legs = await repo.list_topup_legs_for_rates(workspace.id, wallet_id=wallet.id, date_from=None, date_to=None)

    assert len(legs) == 2


async def test_list_topup_legs_for_rates_isolated_by_workspace(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    rub, cny, wallet_other, income_other, _ = await make_topup_environment(db_session, other)
    repo = TransactionRepository(db_session)
    await repo.add(make_cross_topup(other.id, wallet_other.id, income_other.id, rub, cny))
    await db_session.flush()

    assert await repo.list_topup_legs_for_rates(owner.id, wallet_id=None, date_from=None, date_to=None) == []
    assert len(await repo.list_topup_legs_for_rates(other.id, wallet_id=None, date_from=None, date_to=None)) == 2
