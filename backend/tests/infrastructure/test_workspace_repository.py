from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import (
    Category,
    CategoryType,
    Currency,
    Transaction,
    TransactionLeg,
    User,
    Wallet,
    Workspace,
)
from models import categories as categories_table
from models import currencies as currencies_table
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
DEFAULT_OCCURRED_AT = datetime(2026, 1, 1)


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


def make_workspace_entity(
    user_id, currency_id, *, name: str = "Воркспейс", created_at: datetime = DEFAULT_CREATED_AT
) -> Workspace:
    return Workspace(id=uuid4(), user_id=user_id, name=name, currency_id=currency_id, created_at=created_at)


async def test_add_and_get_by_id(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(user.id, workspace_currency.id, name="Поездка в Китай")

    added = await repo.add(workspace)
    await db_session.flush()

    assert added.name == "Поездка в Китай"
    fetched = await repo.get_by_id(workspace.id, user.id)
    assert fetched is not None
    assert fetched.name == "Поездка в Китай"


async def test_get_by_id_unknown_workspace_returns_none(db_session: AsyncSession) -> None:
    repo = WorkspaceRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_get_by_id_with_foreign_owner_returns_none(
    db_session: AsyncSession, workspace_currency: Currency
) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(owner.id, workspace_currency.id)
    await repo.add(workspace)
    await db_session.flush()

    assert await repo.get_by_id(workspace.id, other.id) is None


async def test_list_is_sorted_by_created_at_then_id(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    first = make_workspace_entity(user.id, workspace_currency.id, name="A", created_at=later)
    second = make_workspace_entity(user.id, workspace_currency.id, name="B", created_at=same_moment)
    third = make_workspace_entity(user.id, workspace_currency.id, name="C", created_at=same_moment)
    for workspace in (first, second, third):
        await repo.add(workspace)
    await db_session.flush()

    items = await repo.list(user.id, limit=20, offset=0)

    same_moment_ids_sorted = sorted([second.id, third.id])
    assert [item.id for item in items] == [*same_moment_ids_sorted, first.id]


async def test_count_matches_user_workspaces(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    await repo.add(make_workspace_entity(user_a.id, workspace_currency.id, name="A1"))
    await repo.add(make_workspace_entity(user_a.id, workspace_currency.id, name="A2"))
    await repo.add(make_workspace_entity(user_b.id, workspace_currency.id, name="B1"))
    await db_session.flush()

    assert await repo.count(user_a.id) == 2
    assert await repo.count(user_b.id) == 1


async def test_update_replaces_name(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(user.id, workspace_currency.id, name="Старое")
    await repo.add(workspace)
    await db_session.flush()

    updated = await repo.update(
        workspace.id, user.id, name="Новое", currency_id=workspace_currency.id, now=datetime(2026, 2, 1, tzinfo=UTC)
    )
    await db_session.flush()

    assert updated is not None
    assert updated.name == "Новое"
    assert updated.updated_at == datetime(2026, 2, 1, tzinfo=UTC)


async def test_update_replaces_currency(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user = await make_user(db_session)
    other_currency = await make_workspace_currency(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(user.id, workspace_currency.id)
    await repo.add(workspace)
    await db_session.flush()

    updated = await repo.update(
        workspace.id, user.id, name=workspace.name, currency_id=other_currency.id, now=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert updated is not None
    assert updated.currency_id == other_currency.id


async def test_currency_in_use_by_workspace_cannot_be_deleted(
    db_session: AsyncSession, workspace_currency: Currency
) -> None:
    user = await make_user(db_session)
    await WorkspaceRepository(db_session).add(make_workspace_entity(user.id, workspace_currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(delete(currencies_table).where(currencies_table.c.id == workspace_currency.id))


async def test_workspace_with_unknown_currency_is_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)

    with pytest.raises(IntegrityError):
        await WorkspaceRepository(db_session).add(make_workspace_entity(user.id, uuid4()))
        await db_session.flush()


async def test_update_with_foreign_owner_returns_none(db_session: AsyncSession, workspace_currency: Currency) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(owner.id, workspace_currency.id, name="Моё")
    await repo.add(workspace)
    await db_session.flush()

    result = await repo.update(
        workspace.id, other.id, name="Чужое", currency_id=workspace_currency.id, now=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert result is None
    unchanged = await repo.get_by_id(workspace.id, owner.id)
    assert unchanged is not None
    assert unchanged.name == "Моё"


async def test_delete_success(db_session: AsyncSession, workspace_currency: Currency) -> None:
    user = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(user.id, workspace_currency.id)
    await repo.add(workspace)
    await db_session.flush()

    deleted = await repo.delete(workspace.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(workspace.id, user.id) is None


async def test_delete_with_foreign_owner_returns_false(db_session: AsyncSession, workspace_currency: Currency) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(owner.id, workspace_currency.id)
    await repo.add(workspace)
    await db_session.flush()

    deleted = await repo.delete(workspace.id, other.id)

    assert deleted is False
    assert await repo.get_by_id(workspace.id, owner.id) is not None


async def test_delete_unknown_workspace_returns_false(db_session: AsyncSession) -> None:
    repo = WorkspaceRepository(db_session)

    assert await repo.delete(uuid4(), uuid4()) is False


class TestWorkspaceIsolationWithinSameUser:
    """Полная изоляция между воркспейсами ОДНОГО пользователя — не только между разными пользователями."""

    async def test_wallets_are_isolated_between_workspaces(
        self, db_session: AsyncSession, workspace_currency: Currency
    ) -> None:
        user = await make_user(db_session)
        workspaces = WorkspaceRepository(db_session)
        workspace_a = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка A"))
        workspace_b = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка B"))
        await db_session.flush()
        rub = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
        await CurrencyRepository(db_session).upsert_many([rub])
        wallets = WalletRepository(db_session)
        wallet_a = await wallets.add(
            Wallet(
                id=uuid4(),
                workspace_id=workspace_a.id,
                name="Кошелёк A",
                icon="wallet",
                currency_id=rub.id,
                created_at=DEFAULT_CREATED_AT,
            )
        )
        await db_session.flush()

        assert await wallets.get_by_id(wallet_a.id, workspace_b.id) is None
        assert await wallets.get_by_id(wallet_a.id, workspace_a.id) is not None
        assert await wallets.count(workspace_b.id) == 0
        assert await wallets.count(workspace_a.id) == 1

    async def test_categories_are_isolated_between_workspaces(
        self, db_session: AsyncSession, workspace_currency: Currency
    ) -> None:
        user = await make_user(db_session)
        workspaces = WorkspaceRepository(db_session)
        workspace_a = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка A"))
        workspace_b = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка B"))
        await db_session.flush()
        categories = CategoryRepository(db_session)
        # Одинаковое название и тип в разных воркспейсах одного пользователя — не конфликт (уникальность
        # теперь в пределах workspace_id, а не user_id).
        category_a = await categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace_a.id,
                type=CategoryType.INCOME,
                name="Зарплата",
                icon="wallet",
                created_at=DEFAULT_CREATED_AT,
            )
        )
        category_b = await categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace_b.id,
                type=CategoryType.INCOME,
                name="Зарплата",
                icon="wallet",
                created_at=DEFAULT_CREATED_AT,
            )
        )
        await db_session.flush()

        assert await categories.get_by_id(category_a.id, workspace_b.id) is None
        assert await categories.get_by_id(category_b.id, workspace_a.id) is None
        assert await categories.count(workspace_a.id, type=None) == 1
        assert await categories.count(workspace_b.id, type=None) == 1

    async def test_transactions_are_isolated_between_workspaces(
        self, db_session: AsyncSession, workspace_currency: Currency
    ) -> None:
        user = await make_user(db_session)
        workspaces = WorkspaceRepository(db_session)
        workspace_a = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка A"))
        workspace_b = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id, name="Поездка B"))
        await db_session.flush()
        rub = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
        await CurrencyRepository(db_session).upsert_many([rub])
        wallets = WalletRepository(db_session)
        wallet_a = await wallets.add(
            Wallet(
                id=uuid4(),
                workspace_id=workspace_a.id,
                name="A",
                icon="wallet",
                currency_id=rub.id,
                created_at=DEFAULT_CREATED_AT,
            )
        )
        categories = CategoryRepository(db_session)
        category_a = await categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace_a.id,
                type=CategoryType.INCOME,
                name="Доход",
                icon="wallet",
                created_at=DEFAULT_CREATED_AT,
            )
        )
        transactions = TransactionRepository(db_session)
        transaction = await transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=workspace_a.id,
                wallet_id=wallet_a.id,
                category_id=category_a.id,
                legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("10.00")),),
                occurred_at=DEFAULT_OCCURRED_AT,
                created_at=DEFAULT_CREATED_AT,
            )
        )
        await db_session.flush()

        assert await transactions.get_by_id(transaction.id, workspace_b.id) is None
        transaction_count = await transactions.count(
            workspace_b.id, wallet_id=None, category_id=None, type=None, date_from=None, date_to=None
        )
        assert transaction_count == 0


async def test_deleting_workspace_cascades_to_all_owned_data(
    db_session: AsyncSession, workspace_currency: Currency
) -> None:
    """Удаление воркспейса, в отличие от кошелька/категории, безусловно каскадно чистит все вложенные данные."""
    user = await make_user(db_session)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.add(make_workspace_entity(user.id, workspace_currency.id))
    await db_session.flush()
    rub = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
    await CurrencyRepository(db_session).upsert_many([rub])
    wallets = WalletRepository(db_session)
    wallet_a = await wallets.add(
        Wallet(
            id=uuid4(),
            workspace_id=workspace.id,
            name="A",
            icon="wallet",
            currency_id=rub.id,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    categories = CategoryRepository(db_session)
    category = await categories.add(
        Category(
            id=uuid4(),
            workspace_id=workspace.id,
            type=CategoryType.INCOME,
            name="Доход",
            icon="wallet",
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await TransactionRepository(db_session).add(
        Transaction(
            id=uuid4(),
            workspace_id=workspace.id,
            wallet_id=wallet_a.id,
            category_id=category.id,
            legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("10.00")),),
            occurred_at=DEFAULT_OCCURRED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await db_session.flush()

    # Удаление напрямую на уровне БД — так же, как это делает WorkspaceRepository.delete, без RESTRICT-проверок,
    # которые есть у кошелька/категории (design.md, decision 3): здесь важно поведение самого ON DELETE CASCADE.
    deleted = await workspaces.delete(workspace.id, user.id)
    await db_session.flush()

    assert deleted is True
    for table in (wallets_table, categories_table, transactions_table):
        rows = (await db_session.execute(select(table).where(table.c.workspace_id == workspace.id))).all()
        assert rows == []


async def test_get_currency_id_returns_workspace_currency(
    db_session: AsyncSession, workspace_currency: Currency
) -> None:
    user = await make_user(db_session)
    repo = WorkspaceRepository(db_session)
    workspace = make_workspace_entity(user.id, workspace_currency.id)
    await repo.add(workspace)
    await db_session.flush()

    assert await repo.get_currency_id(workspace.id) == workspace_currency.id


async def test_get_currency_id_unknown_workspace_returns_none(db_session: AsyncSession) -> None:
    assert await WorkspaceRepository(db_session).get_currency_id(uuid4()) is None
