from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, TransactionLeg, User, Wallet, Workspace
from core.exceptions import ClientError, NotFoundError
from core.services.balance import BalanceService
from core.services.topup import TopupService
from core.services.topup_legs import CrossCurrencyTopupLegs, SameCurrencyTopupLegs
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
    """Сервис пополнений на настоящих репозиториях: воркспейс в CNY, кошельки в CNY и RUB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transactions = TransactionRepository(session)
        self.categories = CategoryRepository(session)
        self.wallets = WalletRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.service = TopupService(
            self.transactions,
            self.wallets,
            self.categories,
            CurrencyRepository(session),
            self.workspaces,
            (SameCurrencyTopupLegs(), CrossCurrencyTopupLegs()),
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


async def test_cross_currency_topup_is_stored_with_both_legs(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    topup = await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.rub_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.rub, "10000.00"), leg(env.cny, "780.00")],
        occurred_at=None,
        comment="Обмен",
    )

    stored = await env.service.get_topup(topup.id, env.workspace.id)
    assert {item.currency_id: item.amount for item in stored.legs} == {
        env.cny.id: Decimal("780.00"),
        env.rub.id: Decimal("10000.00"),
    }
    assert [item.currency_id for item in stored.legs] == [env.cny.id, env.rub.id]
    assert stored.comment == "Обмен"


async def test_same_currency_topup_is_stored_with_single_leg(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    topup = await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.cny_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "50")],
        occurred_at=None,
    )

    assert len((await env.service.get_topup(topup.id, env.workspace.id)).legs) == 1


async def test_wrong_leg_set_is_rejected_and_nothing_is_stored(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            env.workspace.id,
            wallet_id=env.rub_wallet.id,
            category_id=env.income.id,
            legs=[leg(env.rub, "1")],
            occurred_at=None,
        )

    _, total = await env.service.list_topups(
        env.workspace.id, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )
    assert total == 0


async def test_update_replaces_legs_in_database(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    topup = await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.rub_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "780"), leg(env.rub, "10000")],
        occurred_at=None,
    )

    updated = await env.service.update_topup(
        topup.id,
        env.workspace.id,
        wallet_id=env.cny_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "5")],
        occurred_at=None,
    )

    assert updated.wallet_id == env.cny_wallet.id
    assert updated.legs == (leg(env.cny, "5"),)
    leg_count = (
        await db_session.execute(
            select(func.count())
            .select_from(transaction_legs_table)
            .where(transaction_legs_table.c.transaction_id == topup.id)
        )
    ).scalar_one()
    assert leg_count == 1


async def test_delete_removes_topup_and_legs(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    topup = await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.rub_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "780"), leg(env.rub, "10000")],
        occurred_at=None,
    )

    await env.service.delete_topup(topup.id, env.workspace.id)

    with pytest.raises(NotFoundError):
        await env.service.get_topup(topup.id, env.workspace.id)
    leg_count = (
        await db_session.execute(
            select(func.count())
            .select_from(transaction_legs_table)
            .where(transaction_legs_table.c.transaction_id == topup.id)
        )
    ).scalar_one()
    assert leg_count == 0


async def test_list_returns_only_topups_of_own_workspace(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    other_workspace = await env.workspace_(env.user)
    other_wallet = await env.wallet(other_workspace, env.cny)
    other_income = await env.category(other_workspace, CategoryType.INCOME)
    mine = await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.cny_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "1")],
        occurred_at=None,
    )
    theirs = await env.service.create_topup(
        other_workspace.id,
        wallet_id=other_wallet.id,
        category_id=other_income.id,
        legs=[leg(env.cny, "2")],
        occurred_at=None,
    )

    items, total = await env.service.list_topups(
        env.workspace.id, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert [item.id for item in items] == [mine.id]
    with pytest.raises(NotFoundError):
        await env.service.get_topup(theirs.id, env.workspace.id)
    with pytest.raises(NotFoundError):
        await env.service.update_topup(
            theirs.id,
            env.workspace.id,
            wallet_id=env.cny_wallet.id,
            category_id=env.income.id,
            legs=[leg(env.cny, "3")],
            occurred_at=None,
        )
    with pytest.raises(NotFoundError):
        await env.service.delete_topup(theirs.id, env.workspace.id)


async def test_foreign_workspace_wallet_and_category_are_rejected(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    other_workspace = await env.workspace_(env.user)
    other_wallet = await env.wallet(other_workspace, env.cny)
    other_income = await env.category(other_workspace, CategoryType.INCOME)

    with pytest.raises(NotFoundError):
        await env.service.create_topup(
            env.workspace.id,
            wallet_id=other_wallet.id,
            category_id=env.income.id,
            legs=[leg(env.cny, "1")],
            occurred_at=None,
        )
    with pytest.raises(NotFoundError):
        await env.service.create_topup(
            env.workspace.id,
            wallet_id=env.cny_wallet.id,
            category_id=other_income.id,
            legs=[leg(env.cny, "1")],
            occurred_at=None,
        )


async def test_expense_is_not_a_topup(db_session: AsyncSession) -> None:
    env = await make_env(db_session)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            env.workspace.id,
            wallet_id=env.cny_wallet.id,
            category_id=env.expense.id,
            legs=[leg(env.cny, "1")],
            occurred_at=None,
        )


async def test_balance_counts_wallet_currency_leg_only(db_session: AsyncSession) -> None:
    env = await make_env(db_session)
    await env.service.create_topup(
        env.workspace.id,
        wallet_id=env.rub_wallet.id,
        category_id=env.income.id,
        legs=[leg(env.cny, "780"), leg(env.rub, "10000")],
        occurred_at=None,
    )
    balance = BalanceService(env.wallets, [env.transactions, TransferRepository(db_session)])

    currency_id, amount = await balance.get_wallet_balance(env.rub_wallet.id, env.workspace.id)

    assert currency_id == env.rub.id
    assert amount == Decimal("10000")
