from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Transaction, TransactionLeg, Wallet, Workspace
from depends.auth import get_current_user
from depends.category import get_category_repository
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository
from main import create_app
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)

CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class Environment:
    def __init__(self, *, authenticated: bool = True) -> None:
        self.categories = InMemoryCategoryRepository()
        self.wallets = InMemoryWalletRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.workspaces = InMemoryWorkspaceRepository()
        self.user_id = uuid4()
        self.rub = uuid4()
        self.cny = uuid4()
        self.income_category_id = uuid4()
        self.workspace_id = uuid4()
        self.workspaces.seed(
            Workspace(
                id=self.workspace_id, user_id=self.user_id, created_at=CREATED_AT, name="Т", currency_id=self.rub
            )
        )
        app = create_app()
        app.dependency_overrides[get_wallet_repository] = lambda: self.wallets
        app.dependency_overrides[get_category_repository] = lambda: self.categories
        app.dependency_overrides[get_transaction_repository] = lambda: self.transactions
        app.dependency_overrides[get_workspace_repository] = lambda: self.workspaces
        if authenticated:
            app.dependency_overrides[get_current_user] = lambda: self.user_id
        self.client = TestClient(app)

    async def make_wallet(self, currency_id: UUID) -> Wallet:
        wallet = Wallet(
            id=uuid4(),
            workspace_id=self.workspace_id,
            name="Кошелёк",
            icon="wallet",
            currency_id=currency_id,
            created_at=CREATED_AT,
        )
        return await self.wallets.add(wallet)

    async def topup(self, wallet: Wallet, rub: str, cny: str) -> None:
        if await self.categories.get_by_id(self.income_category_id, self.workspace_id) is None:
            await self.categories.add(
                Category(
                    id=self.income_category_id,
                    workspace_id=self.workspace_id,
                    type=CategoryType.INCOME,
                    name="Доход",
                    icon="wallet",
                    created_at=CREATED_AT,
                )
            )
        await self.transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=self.workspace_id,
                wallet_id=wallet.id,
                category_id=self.income_category_id,
                legs=(
                    TransactionLeg(currency_id=self.rub, amount=Decimal(rub)),
                    TransactionLeg(currency_id=self.cny, amount=Decimal(cny)),
                ),
                occurred_at=CREATED_AT,
                created_at=CREATED_AT,
            )
        )

    def rates_url(self, wallet_id: UUID, workspace_id: UUID | None = None) -> str:
        return f"/api/workspaces/{workspace_id or self.workspace_id}/wallets/{wallet_id}/rates"


async def test_rate_is_average_of_wallet_topups() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)
    await env.topup(wallet, "100", "10")
    await env.topup(wallet, "300", "20")

    response = env.client.get(env.rates_url(wallet.id))

    assert response.status_code == 200
    assert response.json() == {
        "workspace_currency_id": str(env.rub),
        "wallet_currency_id": str(env.cny),
        "rate": "12.5000000000",
    }


async def test_rate_is_null_without_topups() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)

    response = env.client.get(env.rates_url(wallet.id))

    assert response.status_code == 200
    assert response.json()["rate"] is None


async def test_rate_is_one_for_workspace_currency_wallet() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.rub)

    response = env.client.get(env.rates_url(wallet.id))

    assert response.status_code == 200
    assert response.json() == {
        "workspace_currency_id": str(env.rub),
        "wallet_currency_id": str(env.rub),
        "rate": "1.0000000000",
    }


async def test_rate_is_not_mixed_between_wallets() -> None:
    env = Environment()
    first = await env.make_wallet(env.cny)
    second = await env.make_wallet(env.cny)
    await env.topup(second, "100", "10")

    assert env.client.get(env.rates_url(first.id)).json()["rate"] is None
    assert env.client.get(env.rates_url(second.id)).json()["rate"] == "10.0000000000"


async def test_unknown_wallet_returns_404() -> None:
    env = Environment()

    assert env.client.get(env.rates_url(uuid4())).status_code == 404


async def test_foreign_workspace_returns_404() -> None:
    env = Environment()
    wallet = await env.make_wallet(env.cny)

    assert env.client.get(env.rates_url(wallet.id, uuid4())).status_code == 404


async def test_requires_authentication() -> None:
    env = Environment(authenticated=False)
    wallet = await env.make_wallet(env.cny)

    assert env.client.get(env.rates_url(wallet.id)).status_code == 401
