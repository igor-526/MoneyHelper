from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, User, Wallet
from core.exceptions import AlreadyExistsError, ConflictError
from models import categories as categories_table
from models import users as users_table
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


def make_category(
    user_id: UUID,
    *,
    type: CategoryType = CategoryType.INCOME,
    name: str = "Зарплата",
    icon: str = "wallet",
    created_at: datetime = DEFAULT_CREATED_AT,
) -> Category:
    return Category(id=uuid4(), user_id=user_id, type=type, name=name, icon=icon, created_at=created_at)


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(user.id, name="Зарплата")

    added = await repo.add(category)
    await db_session.flush()

    assert added.name == "Зарплата"
    fetched = await repo.get_by_id(category.id, user.id)
    assert fetched is not None
    assert fetched.name == "Зарплата"
    assert fetched.type == CategoryType.INCOME


async def test_get_by_id_unknown_category_returns_none(db_session: AsyncSession) -> None:
    repo = CategoryRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_get_by_id_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(owner.id)
    await repo.add(category)
    await db_session.flush()

    assert await repo.get_by_id(category.id, other.id) is None


async def test_list_is_sorted_by_created_at_then_id(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    first = make_category(user.id, name="A", created_at=later)
    second = make_category(user.id, name="B", created_at=same_moment)
    third = make_category(user.id, name="C", created_at=same_moment)
    for category in (first, second, third):
        await repo.add(category)
    await db_session.flush()

    items = await repo.list(user.id, type=None, limit=20, offset=0)

    same_moment_ids_sorted = sorted([second.id, third.id])
    assert [item.id for item in items] == [*same_moment_ids_sorted, first.id]


async def test_list_and_count_filter_by_type(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user.id, type=CategoryType.INCOME, name="Зарплата"))
    await repo.add(make_category(user.id, type=CategoryType.EXPENSE, name="Продукты"))
    await db_session.flush()

    income_items = await repo.list(user.id, type=CategoryType.INCOME, limit=20, offset=0)
    all_items = await repo.list(user.id, type=None, limit=20, offset=0)

    assert [item.type for item in income_items] == [CategoryType.INCOME]
    assert len(all_items) == 2
    assert await repo.count(user.id, type=CategoryType.INCOME) == 1
    assert await repo.count(user.id, type=None) == 2


async def test_count_matches_user_categories(db_session: AsyncSession) -> None:
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user_a.id, name="A1"))
    await repo.add(make_category(user_a.id, name="A2"))
    await repo.add(make_category(user_b.id, name="B1"))
    await db_session.flush()

    assert await repo.count(user_a.id, type=None) == 2
    assert await repo.count(user_b.id, type=None) == 1


async def test_update_replaces_type_name_and_icon(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(user.id, type=CategoryType.INCOME, name="Старое")
    await repo.add(category)
    await db_session.flush()

    updated = await repo.update(
        category.id,
        user.id,
        type=CategoryType.EXPENSE,
        name="Новое",
        icon="banknote",
        now=datetime(2026, 2, 1, tzinfo=UTC),
    )
    await db_session.flush()

    assert updated is not None
    assert updated.type == CategoryType.EXPENSE
    assert updated.name == "Новое"
    assert updated.icon == "banknote"
    assert updated.updated_at == datetime(2026, 2, 1, tzinfo=UTC)


async def test_update_unknown_category_returns_none(db_session: AsyncSession) -> None:
    repo = CategoryRepository(db_session)

    result = await repo.update(
        uuid4(), uuid4(), type=CategoryType.INCOME, name="X", icon="wallet", now=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert result is None


async def test_update_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(owner.id, name="Моё")
    await repo.add(category)
    await db_session.flush()

    result = await repo.update(
        category.id,
        other.id,
        type=CategoryType.EXPENSE,
        name="Чужое",
        icon="banknote",
        now=datetime(2026, 2, 1, tzinfo=UTC),
    )

    assert result is None
    unchanged = await repo.get_by_id(category.id, owner.id)
    assert unchanged is not None
    assert unchanged.name == "Моё"


async def test_delete_success(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(user.id)
    await repo.add(category)
    await db_session.flush()

    deleted = await repo.delete(category.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(category.id, user.id) is None


async def test_delete_with_foreign_user_id_returns_false(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(owner.id)
    await repo.add(category)
    await db_session.flush()

    deleted = await repo.delete(category.id, other.id)

    assert deleted is False
    assert await repo.get_by_id(category.id, owner.id) is not None


async def test_delete_unknown_category_returns_false(db_session: AsyncSession) -> None:
    repo = CategoryRepository(db_session)

    assert await repo.delete(uuid4(), uuid4()) is False


async def test_add_duplicate_name_within_type_raises_already_exists(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user.id, type=CategoryType.INCOME, name="Зарплата"))
    await db_session.flush()

    with pytest.raises(AlreadyExistsError):
        await repo.add(make_category(user.id, type=CategoryType.INCOME, name="Зарплата"))


async def test_update_into_taken_name_within_type_raises_already_exists(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user.id, type=CategoryType.INCOME, name="A"))
    category_b = make_category(user.id, type=CategoryType.INCOME, name="B")
    await repo.add(category_b)
    await db_session.flush()

    with pytest.raises(AlreadyExistsError):
        await repo.update(
            category_b.id,
            user.id,
            type=CategoryType.INCOME,
            name="A",
            icon="wallet",
            now=datetime(2026, 2, 1, tzinfo=UTC),
        )


async def test_same_name_allowed_for_different_type_same_user(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user.id, type=CategoryType.INCOME, name="Прочее"))
    await db_session.flush()

    added = await repo.add(make_category(user.id, type=CategoryType.EXPENSE, name="Прочее"))

    assert added.name == "Прочее"


async def test_same_name_allowed_for_same_type_different_user(db_session: AsyncSession) -> None:
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    repo = CategoryRepository(db_session)
    await repo.add(make_category(user_a.id, type=CategoryType.INCOME, name="Зарплата"))
    await db_session.flush()

    added = await repo.add(make_category(user_b.id, type=CategoryType.INCOME, name="Зарплата"))

    assert added.name == "Зарплата"


async def test_check_constraint_rejects_invalid_type(db_session: AsyncSession) -> None:
    user = await make_user(db_session)

    with pytest.raises((IntegrityError, ProgrammingError)):
        await db_session.execute(
            insert(categories_table).values(
                id=uuid4(),
                user_id=user.id,
                type="savings",
                name="Невалидная",
                icon="wallet",
                created_at=DEFAULT_CREATED_AT,
            )
        )


async def test_deleting_user_cascades_to_categories(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = CategoryRepository(db_session)
    category = make_category(user.id)
    await repo.add(category)
    await db_session.flush()

    await db_session.execute(delete(users_table).where(users_table.c.id == user.id))
    await db_session.flush()

    rows = (await db_session.execute(select(categories_table).where(categories_table.c.id == category.id))).all()
    assert rows == []


async def test_delete_category_with_transactions_raises_conflict_error(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    category_repo = CategoryRepository(db_session)
    category = await category_repo.add(make_category(user.id))
    currency = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
    await CurrencyRepository(db_session).upsert_many([currency])
    wallet = await WalletRepository(db_session).add(
        Wallet(
            id=uuid4(),
            user_id=user.id,
            name="Кошелёк",
            icon="wallet",
            currency_ids=(currency.id,),
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await TransactionRepository(db_session).add(
        Transaction(
            id=uuid4(),
            user_id=user.id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("10.00")),),
            occurred_at=DEFAULT_CREATED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await db_session.flush()

    with pytest.raises(ConflictError):
        await category_repo.delete(category.id, user.id)
