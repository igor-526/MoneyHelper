from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Wallet
from depends.auth import get_current_user
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from depends.transfer import get_transfer_repository
from depends.wallet import get_wallet_repository
from main import create_app
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryTransferRepository,
    InMemoryWalletRepository,
)


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    transfers: InMemoryTransferRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    transfers = transfers if transfers is not None else InMemoryTransferRepository()
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    app.dependency_overrides[get_transfer_repository] = lambda: transfers
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app)


async def make_currency(
    currencies: InMemoryCurrencyRepository, code: str = "RUB", decimal_places: int = 2
) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await currencies.upsert_many([currency])
    return currency


async def make_wallet(wallets: InMemoryWalletRepository, user_id: UUID, currency_ids: list[UUID]) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        user_id=user_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=tuple(currency_ids),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def make_category(
    categories: InMemoryCategoryRepository,
    user_id: UUID,
    type: CategoryType = CategoryType.INCOME,
    name: str | None = None,
) -> Category:
    category = Category(
        id=uuid4(),
        user_id=user_id,
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
    user_id: UUID,
) -> tuple[
    InMemoryWalletRepository, InMemoryCategoryRepository, InMemoryCurrencyRepository, Wallet, Category, Currency
]:
    wallets = InMemoryWalletRepository()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    currency = await make_currency(currencies)
    wallet = await make_wallet(wallets, user_id, [currency.id])
    category = await make_category(categories, user_id, CategoryType.INCOME)
    return wallets, categories, currencies, wallet, category, currency


async def test_balance_zero_without_transactions_or_transfers() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, _, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.get(f"/api/wallets/{wallet.id}/balances")

    assert response.status_code == 200
    assert response.json() == [{"currency_id": str(currency.id), "balance": "0"}]


async def test_balance_reflects_income_and_expense() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, income, currency = await make_environment(user_id)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
    client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=currency.id, amount="100.00"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=expense.id, currency_id=currency.id, amount="30.00"),
    )

    response = client.get(f"/api/wallets/{wallet.id}/balances")

    assert response.status_code == 200
    assert response.json() == [{"currency_id": str(currency.id), "balance": "70.00"}]


async def test_balance_separates_currencies_for_multicurrency_wallet() -> None:
    user_id = uuid4()
    wallets, categories, currencies, _, income, rub = await make_environment(user_id)
    cny = await make_currency(currencies, "CNY")
    wallet = await make_wallet(wallets, user_id, [rub.id, cny.id])
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
    client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=rub.id, amount="100.00"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=cny.id, amount="50.00"),
    )

    response = client.get(f"/api/wallets/{wallet.id}/balances")

    assert response.status_code == 200
    balances = {item["currency_id"]: item["balance"] for item in response.json()}
    assert balances == {str(rub.id): "100.00", str(cny.id): "50.00"}


async def test_balance_unknown_or_foreign_wallet_returns_404() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, _, _ = await make_environment(uuid4())
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    assert client.get(f"/api/wallets/{uuid4()}/balances").status_code == 404
    assert client.get(f"/api/wallets/{wallet.id}/balances").status_code == 404


async def test_balance_accounts_for_transfers() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet_a, _, currency = await make_environment(user_id)
    wallet_b = await make_wallet(wallets, user_id, [currency.id])
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    # wallet_a -> wallet_b: 40 (списание с wallet_a, зачисление на wallet_b)
    client.post(
        "/api/transfers",
        json=transfer_payload(
            from_wallet_id=wallet_a.id, to_wallet_id=wallet_b.id, currency_id=currency.id, amount="40.00"
        ),
    )
    # wallet_b -> wallet_a: 15 (зачисление на wallet_a, списание с wallet_b)
    client.post(
        "/api/transfers",
        json=transfer_payload(
            from_wallet_id=wallet_b.id, to_wallet_id=wallet_a.id, currency_id=currency.id, amount="15.00"
        ),
    )

    response_a = client.get(f"/api/wallets/{wallet_a.id}/balances")
    response_b = client.get(f"/api/wallets/{wallet_b.id}/balances")

    assert response_a.status_code == 200
    assert response_a.json() == [{"currency_id": str(currency.id), "balance": "-25.00"}]
    assert response_b.status_code == 200
    assert response_b.json() == [{"currency_id": str(currency.id), "balance": "25.00"}]
