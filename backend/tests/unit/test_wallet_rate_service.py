from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Category, CategoryType, Transaction, TransactionLeg, Wallet, Workspace
from core.exceptions import NotFoundError
from core.services.wallet_rate import WalletRateService
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)

CREATED_AT = datetime(2026, 1, 15, tzinfo=UTC)


class Environment:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.wallets = InMemoryWalletRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.service = WalletRateService(self.wallets, self.workspaces, self.transactions)
        self.rub = uuid4()
        self.cny = uuid4()
        self.workspace_id = self.make_workspace()

    def make_workspace(self) -> UUID:
        workspace = Workspace(id=uuid4(), user_id=uuid4(), name="Т", currency_id=self.rub, created_at=CREATED_AT)
        self.workspaces.seed(workspace)
        return workspace.id

    async def make_wallet(self, currency_id: UUID, workspace_id: UUID | None = None) -> Wallet:
        wallet = Wallet(
            id=uuid4(),
            workspace_id=workspace_id or self.workspace_id,
            name="Alipay",
            icon="wallet",
            currency_id=currency_id,
            created_at=CREATED_AT,
        )
        return await self.wallets.add(wallet)

    async def topup(self, wallet: Wallet, rub: str, cny: str, type: CategoryType = CategoryType.INCOME) -> None:
        category = await self.categories.add(
            Category(
                id=uuid4(),
                workspace_id=wallet.workspace_id,
                type=type,
                name=f"К {uuid4()}",
                icon="wallet",
                created_at=CREATED_AT,
            )
        )
        await self.transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=wallet.workspace_id,
                wallet_id=wallet.id,
                category_id=category.id,
                legs=(
                    TransactionLeg(currency_id=self.rub, amount=Decimal(rub)),
                    TransactionLeg(currency_id=self.cny, amount=Decimal(cny)),
                ),
                occurred_at=CREATED_AT,
                created_at=CREATED_AT,
            )
        )


async def test_rate_is_simple_average_over_wallet_topups() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)
    await env.topup(wallet, "100", "10")
    await env.topup(wallet, "300", "20")

    result = await env.service.get_wallet_rate(wallet.id, env.workspace_id)

    assert result.workspace_currency_id == env.rub
    assert result.wallet_currency_id == env.cny
    assert result.rate == Decimal("12.5")


async def test_rate_is_rounded_to_rate_precision() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)
    await env.topup(wallet, "10", "3")

    result = await env.service.get_wallet_rate(wallet.id, env.workspace_id)

    assert result.rate == Decimal("3.3333333333")


async def test_rate_is_not_mixed_between_wallets() -> None:
    env = Environment()
    first = await env.make_wallet(env.cny)
    second = await env.make_wallet(env.cny)
    await env.topup(second, "100", "10")

    assert (await env.service.get_wallet_rate(first.id, env.workspace_id)).rate is None
    assert (await env.service.get_wallet_rate(second.id, env.workspace_id)).rate == Decimal("10")


async def test_rate_is_not_mixed_between_workspaces() -> None:
    env = Environment()
    other_workspace_id = env.make_workspace()
    other_wallet = await env.make_wallet(env.cny, other_workspace_id)
    await env.topup(other_wallet, "100", "10")
    wallet = await env.make_wallet(env.cny)

    assert (await env.service.get_wallet_rate(wallet.id, env.workspace_id)).rate is None


async def test_non_topup_operations_are_ignored() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)
    await env.topup(wallet, "100", "10", CategoryType.EXPENSE)

    assert (await env.service.get_wallet_rate(wallet.id, env.workspace_id)).rate is None


async def test_rate_is_one_when_currencies_match() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.rub)

    result = await env.service.get_wallet_rate(wallet.id, env.workspace_id)

    assert result.rate == Decimal("1")


async def test_rate_is_none_without_topups() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)

    assert (await env.service.get_wallet_rate(wallet.id, env.workspace_id)).rate is None


async def test_unknown_wallet_raises_not_found() -> None:
    env = Environment()

    with pytest.raises(NotFoundError):
        await env.service.get_wallet_rate(uuid4(), env.workspace_id)


async def test_foreign_wallet_raises_not_found() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)

    with pytest.raises(NotFoundError):
        await env.service.get_wallet_rate(wallet.id, env.make_workspace())
