from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Wallet, Workspace
from depends.auth import get_current_user
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository
from main import create_app
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)

DATE_FROM = "2026-01-01T00:00:00Z"
DATE_TO = "2026-01-31T00:00:00Z"
IN_RANGE = datetime(2026, 1, 15, tzinfo=UTC)


class Environment:
    """Воркспейс в RUB с кошельками в RUB и CNY; пополнение CNY-кошелька: 1000 RUB / 100 CNY (курс 10)."""

    def __init__(self, *, authenticated: bool = True) -> None:
        self.categories = InMemoryCategoryRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.wallets = InMemoryWalletRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.user_id = uuid4()
        self.workspace_id = uuid4()
        self.rub = Currency(id=uuid4(), code="RUB", name="RUB", decimal_places=2)
        self.cny = Currency(id=uuid4(), code="CNY", name="CNY", decimal_places=2)
        self.usd = Currency(id=uuid4(), code="USD", name="USD", decimal_places=2)
        self.workspaces.seed(
            Workspace(
                id=self.workspace_id, user_id=self.user_id, created_at=IN_RANGE, name="Т", currency_id=self.rub.id
            )
        )
        app = create_app()
        app.dependency_overrides[get_category_repository] = lambda: self.categories
        app.dependency_overrides[get_currency_repository] = lambda: self.currencies
        app.dependency_overrides[get_transaction_repository] = lambda: self.transactions
        app.dependency_overrides[get_wallet_repository] = lambda: self.wallets
        app.dependency_overrides[get_workspace_repository] = lambda: self.workspaces
        if authenticated:
            app.dependency_overrides[get_current_user] = lambda: self.user_id
        self.client = TestClient(app)

    async def setup(self) -> None:
        await self.currencies.upsert_many([self.rub, self.cny, self.usd])
        self.rub_wallet = await self.make_wallet(self.rub)
        self.cny_wallet = await self.make_wallet(self.cny)
        self.income = await self.make_category(CategoryType.INCOME)
        self.expense = await self.make_category(CategoryType.EXPENSE)

    async def make_wallet(self, currency: Currency) -> UUID:
        wallet = Wallet(
            id=uuid4(),
            workspace_id=self.workspace_id,
            name="К",
            icon="wallet",
            currency_id=currency.id,
            created_at=IN_RANGE,
        )
        return (await self.wallets.add(wallet)).id

    async def make_category(self, type: CategoryType) -> UUID:
        category = Category(
            id=uuid4(), workspace_id=self.workspace_id, type=type, name="К", icon="wallet", created_at=IN_RANGE
        )
        return (await self.categories.add(category)).id

    async def add_operation(self, wallet_id: UUID, category_id: UUID, legs: dict[UUID, str]) -> None:
        await self.transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=self.workspace_id,
                wallet_id=wallet_id,
                category_id=category_id,
                legs=tuple(TransactionLeg(currency_id=c, amount=Decimal(a)) for c, a in legs.items()),
                occurred_at=IN_RANGE,
                created_at=IN_RANGE,
            )
        )

    async def topup_cny(self) -> None:
        await self.add_operation(self.cny_wallet, self.income, {self.rub.id: "1000", self.cny.id: "100"})

    def get(self, group_by: str = "wallet", **params: str) -> Any:
        query: dict[str, str] = {"date_from": DATE_FROM, "date_to": DATE_TO, "group_by": group_by, **params}
        return self.client.get(f"/api/workspaces/{self.workspace_id}/analytics", params=query)


async def test_default_display_currency_is_workspace_currency() -> None:
    env = Environment()
    await env.setup()
    await env.topup_cny()
    await env.add_operation(env.cny_wallet, env.expense, {env.cny.id: "30"})

    response = env.get()

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency_id"] == str(env.rub.id)
    assert body["unconverted_currencies"] == []
    assert body["buckets"] == [{"group_key": str(env.cny_wallet), "income": "1000.00", "expense": "300.00"}]


async def test_wallet_currency_is_allowed_as_display_currency() -> None:
    env = Environment()
    await env.setup()
    await env.topup_cny()

    response = env.get(display_currency=str(env.cny.id))

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency_id"] == str(env.cny.id)
    assert body["buckets"][0]["income"] == "100.00"


async def test_unrelated_display_currency_is_rejected() -> None:
    env = Environment()
    await env.setup()

    assert env.get(display_currency=str(env.usd.id)).status_code == 400
    assert env.get(display_currency=str(uuid4())).status_code == 400


async def test_unconverted_currency_does_not_fail_request() -> None:
    env = Environment()
    await env.setup()
    await env.add_operation(env.cny_wallet, env.expense, {env.cny.id: "30"})
    await env.add_operation(env.rub_wallet, env.expense, {env.rub.id: "5"})

    response = env.get()

    assert response.status_code == 200
    body = response.json()
    assert body["unconverted_currencies"] == [str(env.cny.id)]
    assert [bucket["group_key"] for bucket in body["buckets"]] == [str(env.rub_wallet)]


async def test_group_by_category_and_currency() -> None:
    env = Environment()
    await env.setup()
    await env.topup_cny()
    await env.add_operation(env.rub_wallet, env.expense, {env.rub.id: "30"})

    by_category = env.get("category").json()["buckets"]
    by_currency = env.get("currency").json()["buckets"]

    assert {bucket["group_key"] for bucket in by_category} == {str(env.income), str(env.expense)}
    assert {bucket["group_key"] for bucket in by_currency} == {str(env.rub.id), str(env.cny.id)}


async def test_filters_wallet_category_currency_type() -> None:
    env = Environment()
    await env.setup()
    await env.topup_cny()
    await env.add_operation(env.rub_wallet, env.expense, {env.rub.id: "30"})

    def keys(**params: str) -> set[str]:
        return {bucket["group_key"] for bucket in env.get(**params).json()["buckets"]}

    assert keys(wallet_id=str(env.rub_wallet)) == {str(env.rub_wallet)}
    assert keys(category_id=str(env.income)) == {str(env.cny_wallet)}
    assert keys(currency_id=str(env.cny.id)) == {str(env.cny_wallet)}
    assert keys(type="expense") == {str(env.rub_wallet)}


async def test_missing_dates_and_inverted_range_rejected() -> None:
    env = Environment()
    await env.setup()
    url = f"/api/workspaces/{env.workspace_id}/analytics"

    assert env.client.get(url, params={"date_to": DATE_TO, "group_by": "wallet"}).status_code == 400
    assert env.client.get(url, params={"date_from": DATE_FROM, "group_by": "wallet"}).status_code == 400
    inverted = env.client.get(url, params={"date_from": DATE_TO, "date_to": DATE_FROM, "group_by": "wallet"})
    assert inverted.status_code == 400


async def test_foreign_workspace_returns_404() -> None:
    env = Environment()
    await env.setup()

    response = env.client.get(
        f"/api/workspaces/{uuid4()}/analytics",
        params={"date_from": DATE_FROM, "date_to": DATE_TO, "group_by": "wallet"},
    )

    assert response.status_code == 404


async def test_other_workspace_data_is_excluded() -> None:
    env = Environment()
    await env.setup()
    other_workspace_id = uuid4()
    env.workspaces.seed(
        Workspace(id=other_workspace_id, user_id=env.user_id, created_at=IN_RANGE, name="Д", currency_id=env.rub.id)
    )
    other_wallet = Wallet(
        id=uuid4(),
        workspace_id=other_workspace_id,
        name="К",
        icon="wallet",
        currency_id=env.cny.id,
        created_at=IN_RANGE,
    )
    await env.wallets.add(other_wallet)
    other_income = await env.categories.add(
        Category(
            id=uuid4(),
            workspace_id=other_workspace_id,
            type=CategoryType.INCOME,
            name="Д",
            icon="wallet",
            created_at=IN_RANGE,
        )
    )
    await env.transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=other_workspace_id,
            wallet_id=other_wallet.id,
            category_id=other_income.id,
            legs=(
                TransactionLeg(currency_id=env.rub.id, amount=Decimal("1000")),
                TransactionLeg(currency_id=env.cny.id, amount=Decimal("100")),
            ),
            occurred_at=IN_RANGE,
            created_at=IN_RANGE,
        )
    )
    await env.add_operation(env.cny_wallet, env.expense, {env.cny.id: "30"})

    body = env.get().json()

    assert body["buckets"] == []
    assert body["unconverted_currencies"] == [str(env.cny.id)]


async def test_requires_authentication() -> None:
    env = Environment(authenticated=False)
    await env.setup()

    assert env.get().status_code == 401
