from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Wallet, Workspace
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


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    workspaces = workspaces if workspaces is not None else InMemoryWorkspaceRepository()
    user_id = user_id if user_id is not None else uuid4()
    workspace_id = workspace_id if workspace_id is not None else uuid4()
    workspaces.seed(Workspace(id=workspace_id, user_id=user_id, created_at=datetime(2026, 1, 1, tzinfo=UTC), name="Т"))
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), workspace_id


def rates_url(workspace_id: UUID, wallet_id: UUID, target_currency_id: UUID) -> str:
    return f"/api/workspaces/{workspace_id}/wallets/{wallet_id}/rates?target_currency_id={target_currency_id}"


def topups_url(workspace_id: UUID) -> str:
    return f"/api/workspaces/{workspace_id}/transactions/topups"


async def make_currency(
    currencies: InMemoryCurrencyRepository, code: str = "RUB", decimal_places: int = 2
) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await currencies.upsert_many([currency])
    return currency


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id: UUID, currency_ids: list[UUID]) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=tuple(currency_ids),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def make_income_category(categories: InMemoryCategoryRepository, workspace_id: UUID) -> Category:
    category = Category(
        id=uuid4(),
        workspace_id=workspace_id,
        type=CategoryType.INCOME,
        name=f"Категория {uuid4()}",
        icon="wallet",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await categories.add(category)


EnvironmentTuple = tuple[
    InMemoryWalletRepository,
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    Wallet,
    Currency,
    Currency,
    Category,
]


async def make_environment(workspace_id: UUID) -> EnvironmentTuple:
    wallets = InMemoryWalletRepository()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
    income = await make_income_category(categories, workspace_id)
    return wallets, categories, currencies, wallet, rub, cny, income


def topup_payload(*, wallet_id: UUID, category_id: UUID, legs: list[tuple[UUID, str]]) -> dict:
    return {
        "wallet_id": str(wallet_id),
        "category_id": str(category_id),
        "legs": [{"currency_id": str(currency_id), "amount": amount} for currency_id, amount in legs],
    }


async def test_average_rate_from_topups() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, rub, cny, income = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    client.post(
        topups_url(workspace_id),
        json=topup_payload(
            wallet_id=wallet.id, category_id=income.id, legs=[(rub.id, "10000.00"), (cny.id, "780.00")]
        ),
    )
    client.post(
        topups_url(workspace_id),
        json=topup_payload(wallet_id=wallet.id, category_id=income.id, legs=[(rub.id, "5000.00"), (cny.id, "400.00")]),
    )

    response = client.get(rates_url(workspace_id, wallet.id, rub.id))

    assert response.status_code == 200
    body = response.json()
    assert body["target_currency_id"] == str(rub.id)
    assert body["unrated_currency_ids"] == []
    assert len(body["rates"]) == 1
    assert body["rates"][0]["currency_id"] == str(cny.id)


async def test_currency_without_topups_is_reported_as_unrated() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, rub, cny, _ = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.get(rates_url(workspace_id, wallet.id, rub.id))

    assert response.status_code == 200
    body = response.json()
    assert body["rates"] == []
    assert body["unrated_currency_ids"] == [str(cny.id)]


async def test_missing_target_currency_query_param_is_rejected() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, _, _, _ = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.get(f"/api/workspaces/{workspace_id}/wallets/{wallet.id}/rates")

    assert response.status_code == 400


async def test_target_currency_not_in_wallet_is_rejected() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, _, _, _ = await make_environment(workspace_id)
    other_currency = await make_currency(currencies, "USDT", decimal_places=6)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.get(rates_url(workspace_id, wallet.id, other_currency.id))

    assert response.status_code == 400


async def test_unknown_or_foreign_wallet_returns_404() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, rub, _, _ = await make_environment(workspace_id)
    client, other_workspace_id = make_client(wallets=wallets, categories=categories, currencies=currencies)

    assert client.get(rates_url(other_workspace_id, uuid4(), rub.id)).status_code == 404
    assert client.get(rates_url(other_workspace_id, wallet.id, rub.id)).status_code == 404


async def test_requires_authentication() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, rub, _, _ = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id, authenticated=False
    )

    response = client.get(rates_url(workspace_id, wallet.id, rub.id))

    assert response.status_code == 401
