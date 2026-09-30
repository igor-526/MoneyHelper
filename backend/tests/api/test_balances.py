from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Wallet, Workspace
from depends.auth import get_current_user
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from depends.transfer import get_transfer_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository
from main import create_app
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryTransferRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    transfers: InMemoryTransferRepository | None = None,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    transfers = transfers if transfers is not None else InMemoryTransferRepository()
    workspaces = workspaces if workspaces is not None else InMemoryWorkspaceRepository()
    user_id = user_id if user_id is not None else uuid4()
    workspace_id = workspace_id if workspace_id is not None else uuid4()
    workspaces.seed(Workspace(id=workspace_id, user_id=user_id, created_at=datetime(2026, 1, 1, tzinfo=UTC), name="Т"))
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    app.dependency_overrides[get_transfer_repository] = lambda: transfers
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), workspace_id


def balances_url(workspace_id: UUID, wallet_id: UUID) -> str:
    return f"/api/workspaces/{workspace_id}/wallets/{wallet_id}/balances"


def transactions_url(workspace_id: UUID) -> str:
    return f"/api/workspaces/{workspace_id}/transactions"


def transfers_url(workspace_id: UUID) -> str:
    return f"/api/workspaces/{workspace_id}/transfers"


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


async def make_category(
    categories: InMemoryCategoryRepository,
    workspace_id: UUID,
    type: CategoryType = CategoryType.INCOME,
    name: str | None = None,
) -> Category:
    category = Category(
        id=uuid4(),
        workspace_id=workspace_id,
        type=type,
        name=name if name is not None else f"Категория {uuid4()}",
        icon="wallet",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await categories.add(category)


def transaction_payload(*, wallet_id: UUID, category_id: UUID, currency_id: UUID, amount: str = "100.00") -> dict:
    return {
        "wallet_id": str(wallet_id),
        "category_id": str(category_id),
        "currency_id": str(currency_id),
        "amount": amount,
    }


def transfer_payload(*, from_wallet_id: UUID, to_wallet_id: UUID, currency_id: UUID, amount: str = "10.00") -> dict:
    return {
        "from_wallet_id": str(from_wallet_id),
        "to_wallet_id": str(to_wallet_id),
        "currency_id": str(currency_id),
        "amount": amount,
    }


async def make_environment(
    workspace_id: UUID,
) -> tuple[
    InMemoryWalletRepository, InMemoryCategoryRepository, InMemoryCurrencyRepository, Wallet, Category, Currency
]:
    wallets = InMemoryWalletRepository()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, workspace_id, [currency.id])
    category = await make_category(categories, workspace_id, CategoryType.INCOME)
    return wallets, categories, currencies, wallet, category, currency


async def test_balance_zero_without_transactions_or_transfers() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, _, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.get(balances_url(workspace_id, wallet.id))

    assert response.status_code == 200
    assert response.json() == [{"currency_id": str(currency.id), "balance": "0"}]


async def test_balance_reflects_income_and_expense() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, income, currency = await make_environment(workspace_id)
    expense = await make_category(categories, workspace_id, CategoryType.EXPENSE)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=currency.id, amount="100.00"),
    )
    client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=expense.id, currency_id=currency.id, amount="30.00"),
    )

    response = client.get(balances_url(workspace_id, wallet.id))

    assert response.status_code == 200
    assert response.json() == [{"currency_id": str(currency.id), "balance": "70.00"}]


async def test_balance_separates_currencies_for_multicurrency_wallet() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, _, income, rub = await make_environment(workspace_id)
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=rub.id, amount="100.00"),
    )
    client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=cny.id, amount="50.00"),
    )

    response = client.get(balances_url(workspace_id, wallet.id))

    assert response.status_code == 200
    balances = {item["currency_id"]: item["balance"] for item in response.json()}
    assert balances == {str(rub.id): "100.00", str(cny.id): "50.00"}


async def test_balance_unknown_or_foreign_wallet_returns_404() -> None:
    wallets, categories, currencies, wallet, _, _ = await make_environment(uuid4())
    client, workspace_id = make_client(wallets=wallets, categories=categories, currencies=currencies)

    assert client.get(balances_url(workspace_id, uuid4())).status_code == 404
    assert client.get(balances_url(workspace_id, wallet.id)).status_code == 404


async def test_balance_accounts_for_transfers() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet_a, _, currency = await make_environment(workspace_id)
    wallet_b = await make_wallet(wallets, workspace_id, [currency.id])
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    # wallet_a -> wallet_b: 40 (списание с wallet_a, зачисление на wallet_b)
    client.post(
        transfers_url(workspace_id),
        json=transfer_payload(
            from_wallet_id=wallet_a.id, to_wallet_id=wallet_b.id, currency_id=currency.id, amount="40.00"
        ),
    )
    # wallet_b -> wallet_a: 15 (зачисление на wallet_a, списание с wallet_b)
    client.post(
        transfers_url(workspace_id),
        json=transfer_payload(
            from_wallet_id=wallet_b.id, to_wallet_id=wallet_a.id, currency_id=currency.id, amount="15.00"
        ),
    )

    response_a = client.get(balances_url(workspace_id, wallet_a.id))
    response_b = client.get(balances_url(workspace_id, wallet_b.id))

    assert response_a.status_code == 200
    assert response_a.json() == [{"currency_id": str(currency.id), "balance": "-25.00"}]
    assert response_b.status_code == 200
    assert response_b.json() == [{"currency_id": str(currency.id), "balance": "25.00"}]
