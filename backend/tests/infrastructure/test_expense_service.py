from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, User, Wallet, Workspace
from core.exceptions import ClientError, NotFoundError
from core.services.balance import BalanceService
from core.services.transaction import TransactionService
from models import transaction_legs as transaction_legs_table
from repositories.category import CategoryRepository
from repositories.currency import CurrencyRepository
from repositories.transaction import TransactionRepository
from repositories.transfer import TransferRepository
from repositories.user import UserRepository
from repositories.wallet import WalletRepository
from repositories.workspace import WorkspaceRepository
from tests.fakes import FixedClock, SequentialIdGenerator

pytestmark = pytest.mark.infrastructure

CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class Environment:
    """Сервис расходов на настоящих репозиториях: воркспейс в CNY, кошельки в CNY и RUB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transactions = TransactionRepository(session)
        self.categories = CategoryRepository(session)
        self.wallets = WalletRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.service = TransactionService(
            self.transactions,
            self.wallets,
            self.categories,
            CurrencyRepository(session),
            FixedClock(),
            SequentialIdGenerator(),
        )

    async def setup(self) -> None:
        currencies = CurrencyRepository(self.session)
        self.cny = Currency(id=uuid4(), code=f"C{uuid4().hex[:8].upper()}", name="CNY", decimal_places=2)
        self.rub = Currency(id=uuid4(), code=f"R{uuid4().hex[:8].upper()}", name="RUB", decimal_places=2)
        await currencies.upsert_many([self.cny, self.rub])
        self.user = await self.user_()
        self.workspace = await self.workspace_(self.user)
        self.cny_wallet = await self.wallet(self.workspace, self.cny)
        self.rub_wallet = await self.wallet(self.workspace, self.rub)
        self.income = await self.category(self.workspace, CategoryType.INCOME)
        self.expense = await self.category(self.workspace, CategoryType.EXPENSE)

    async def user_(self) -> User:
        user = User(
            id=uuid4(), email=f"{uuid4()}@example.com", password_hash="hashed", token_version=0, created_at=CREATED_AT
        )
        await UserRepository(self.session).add(user)
        await self.session.flush()
        return user

    async def workspace_(self, user: User) -> Workspace:
        workspace = Workspace(
            id=uuid4(), user_id=user.id, name="Воркспейс", currency_id=self.cny.id, created_at=CREATED_AT
        )
        await self.workspaces.add(workspace)
        await self.session.flush()
        return workspace

    async def wallet(self, workspace: Workspace, currency: Currency) -> Wallet:
        wallet = await self.wallets.add(
            Wallet(
                id=uuid4(),
                workspace_id=workspace.id,
                name="Кошелёк",
                icon="wallet",
                currency_id=currency.id,
                created_at=CREATED_AT,
            )
        )
        await self.session.flush()
        return wallet

    async def category(self, workspace: Workspace, type: CategoryType) -> Category:
        category = await self.categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace.id,
                type=type,
                name=f"Категория {uuid4()}",
                icon="wallet",
                created_at=CREATED_AT,
            )
        )
        await self.session.flush()
        return category


def leg(currency: Currency, amount: str) -> TransactionLeg:
    return TransactionLeg(currency_id=currency.id, amount=Decimal(amount))


async def make_env(db_session: AsyncSession) -> Environment:
    env = Environment(db_session)
    await env.setup()
    return env


async def create_expense(
    env: Environment,
    wallet: Wallet,
    amount: str = "10",
    *,
    category_id: UUID | None = None,
    occurred_at: datetime | None = None,
    comment: str | None = None,
) -> Transaction:
    return await env.service.create_transaction(
        env.workspace.id,
        wallet_id=wallet.id,
        category_id=category_id if category_id is not None else env.expense.id,
        amount=Decimal(amount),
        occurred_at=occurred_at,
        comment=comment,
    )


async def test_expense_is_stored_with_single_leg_in_wallet_currency(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    expense = await create_expense(env, env.rub_wallet, "99.50", comment="Обед")

    stored = await env.service.get_transaction(expense.id, env.workspace.id)
    assert stored.legs == (leg(env.rub, "99.50"),)
    assert stored.comment == "Обед"
    leg_count = (
        await db_session.execute(
            select(func.count())
            .select_from(transaction_legs_table)
            .where(transaction_legs_table.c.transaction_id == expense.id)
        )
    ).scalar_one()
    assert leg_count == 1


async def test_income_category_is_rejected_and_nothing_is_stored(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    with pytest.raises(ClientError):
        await create_expense(env, env.cny_wallet, category_id=env.income.id)

    _, total = await env.service.list_transactions(
        env.workspace.id, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )
    assert total == 0


async def test_update_moves_expense_to_other_wallet_currency(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    expense = await create_expense(env, env.rub_wallet, "10")

    updated = await env.service.update_transaction(
        expense.id,
        env.workspace.id,
        wallet_id=env.cny_wallet.id,
        category_id=env.expense.id,
        amount=Decimal("5"),
        occurred_at=None,
    )

    assert updated.legs == (leg(env.cny, "5"),)


async def test_list_filters_wallet_category_dates_and_paginates(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    other_category = await env.category(env.workspace, CategoryType.EXPENSE)
    await create_expense(env, env.rub_wallet, "1", occurred_at=datetime(2026, 3, 1, tzinfo=UTC))
    await create_expense(env, env.cny_wallet, "2", occurred_at=datetime(2026, 4, 1, tzinfo=UTC))
    await create_expense(
        env, env.cny_wallet, "3", category_id=other_category.id, occurred_at=datetime(2026, 5, 1, tzinfo=UTC)
    )

    async def listing(**filters):  # type: ignore[no-untyped-def]
        params = {
            "wallet_id": None,
            "category_id": None,
            "date_from": None,
            "date_to": None,
            "limit": 20,
            "offset": 0,
        } | filters
        return await env.service.list_transactions(env.workspace.id, **params)

    _, total_all = await listing()
    by_wallet, total_wallet = await listing(wallet_id=env.cny_wallet.id)
    by_category, _ = await listing(category_id=other_category.id)
    by_dates, _ = await listing(date_from=datetime(2026, 3, 15, tzinfo=UTC), date_to=datetime(2026, 4, 15, tzinfo=UTC))
    page, total_page = await listing(limit=1, offset=1)

    assert total_all == 3
    assert total_wallet == 2
    assert [item.legs[0].amount for item in by_wallet] == [Decimal("3"), Decimal("2")]
    assert [item.legs[0].amount for item in by_category] == [Decimal("3")]
    assert [item.legs[0].amount for item in by_dates] == [Decimal("2")]
    assert [item.legs[0].amount for item in page] == [Decimal("2")]
    assert total_page == 3


async def test_list_does_not_contain_income_and_other_workspaces(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    await create_expense(env, env.cny_wallet, "1")
    other_workspace = await env.workspace_(env.user)
    other_wallet = await env.wallet(other_workspace, env.cny)
    other_category = await env.category(other_workspace, CategoryType.EXPENSE)
    await env.service.create_transaction(
        other_workspace.id,
        wallet_id=other_wallet.id,
        category_id=other_category.id,
        amount=Decimal("7"),
        occurred_at=None,
    )

    items, total = await env.service.list_transactions(
        env.workspace.id, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert [item.legs[0].amount for item in items] == [Decimal("1")]


async def test_foreign_workspace_expense_is_not_found(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    expense = await create_expense(env, env.cny_wallet)

    with pytest.raises(NotFoundError):
        await env.service.get_transaction(expense.id, uuid4())


async def test_delete_removes_expense_and_legs(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    expense = await create_expense(env, env.cny_wallet)

    await env.service.delete_transaction(expense.id, env.workspace.id)

    with pytest.raises(NotFoundError):
        await env.service.get_transaction(expense.id, env.workspace.id)
    leg_count = (
        await db_session.execute(
            select(func.count())
            .select_from(transaction_legs_table)
            .where(transaction_legs_table.c.transaction_id == expense.id)
        )
    ).scalar_one()
    assert leg_count == 0


async def test_expense_decreases_wallet_balance(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    await env.transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=env.workspace.id,
            wallet_id=env.cny_wallet.id,
            category_id=env.income.id,
            legs=(leg(env.cny, "100"),),
            occurred_at=CREATED_AT,
            comment=None,
            created_at=CREATED_AT,
        )
    )
    await create_expense(env, env.cny_wallet, "30")
    balances = BalanceService(env.wallets, [env.transactions, TransferRepository(db_session)])

    currency_id, balance = await balances.get_wallet_balance(env.cny_wallet.id, env.workspace.id)

    assert currency_id == env.cny.id
    assert balance == Decimal("70")
