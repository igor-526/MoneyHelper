from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Wallet
from depends.auth import get_current_user
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from main import create_app
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
)


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
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


def transaction_payload(
    *,
    wallet_id: UUID,
    category_id: UUID,
    currency_id: UUID,
    amount: str = "100.00",
    occurred_at: str | None = None,
) -> dict:
    payload = {
        "wallet_id": str(wallet_id),
        "category_id": str(category_id),
        "currency_id": str(currency_id),
        "amount": amount,
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return payload


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


async def test_create_transaction_with_explicit_date() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(
            wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, occurred_at="2026-03-01T12:00:00Z"
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_id"] == str(wallet.id)
    assert body["category_id"] == str(category.id)
    assert body["currency_id"] == str(currency.id)
    assert body["amount"] == "100.00"
    assert body["occurred_at"] == "2026-03-01T12:00:00Z"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_transaction_without_date_uses_server_time() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 201
    assert response.json()["occurred_at"] is not None


async def test_create_transaction_rejects_currency_not_in_wallet() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, _ = await make_environment(user_id)
    other_currency = await make_currency(currencies, "CNY")
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=other_currency.id),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_amount_exceeding_decimal_places() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(
            wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="1.005"
        ),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_nonpositive_amount() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="0"),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_unknown_wallet() -> None:
    user_id = uuid4()
    wallets, categories, currencies, _, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=uuid4(), category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_foreign_wallet() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(uuid4())
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_unknown_category() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, _, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=uuid4(), currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_foreign_category() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(uuid4())
    wallets2 = InMemoryWalletRepository()
    own_wallet = await make_wallet(wallets2, user_id, [currency.id])
    client = make_client(wallets=wallets2, categories=categories, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=own_wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_without_session_is_401() -> None:
    client = make_client(authenticated=False)

    response = client.post(
        "/api/transactions", json=transaction_payload(wallet_id=uuid4(), category_id=uuid4(), currency_id=uuid4())
    )

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    other_category = await make_category(categories, user_id, CategoryType.EXPENSE)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    created = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    ).json()
    transaction_id = created["id"]

    got = client.get(f"/api/transactions/{transaction_id}")
    assert got.status_code == 200
    assert got.json()["id"] == transaction_id

    listed = client.get("/api/transactions")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == transaction_id

    updated = client.put(
        f"/api/transactions/{transaction_id}",
        json=transaction_payload(
            wallet_id=wallet.id, category_id=other_category.id, currency_id=currency.id, amount="55.00"
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["category_id"] == str(other_category.id)
    assert updated.json()["amount"] == "55.00"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(f"/api/transactions/{transaction_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/transactions/{transaction_id}")
    assert after_delete.status_code == 404


async def test_get_unknown_transaction_returns_404() -> None:
    client = make_client()

    response = client.get(f"/api/transactions/{uuid4()}")

    assert response.status_code == 404


async def test_put_unknown_transaction_returns_404() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

    response = client.put(
        f"/api/transactions/{uuid4()}",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    user_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
    other_currency = await make_currency(currencies, "CNY")
    client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
    transaction_id = client.post(
        "/api/transactions",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    ).json()["id"]

    currency_response = client.put(
        f"/api/transactions/{transaction_id}",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=other_currency.id),
    )
    assert currency_response.status_code == 400

    amount_response = client.put(
        f"/api/transactions/{transaction_id}",
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="0"),
    )
    assert amount_response.status_code == 400


async def test_delete_unknown_transaction_returns_404() -> None:
    client = make_client()

    response = client.delete(f"/api/transactions/{uuid4()}")

    assert response.status_code == 404


class TestFiltersAndSorting:
    async def test_filter_by_wallet(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet_a, category, currency = await make_environment(user_id)
        wallet_b = await make_wallet(wallets, user_id, [currency.id])
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet_a.id, category_id=category.id, currency_id=currency.id),
        )
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet_b.id, category_id=category.id, currency_id=currency.id),
        )

        response = client.get("/api/transactions", params={"wallet_id": str(wallet_a.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["wallet_id"] == str(wallet_a.id)

    async def test_filter_by_category(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, category_a, currency = await make_environment(user_id)
        category_b = await make_category(categories, user_id, CategoryType.EXPENSE)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category_a.id, currency_id=currency.id),
        )
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category_b.id, currency_id=currency.id),
        )

        response = client.get("/api/transactions", params={"category_id": str(category_a.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category_id"] == str(category_a.id)

    async def test_filter_by_type(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, income, currency = await make_environment(user_id)
        expense = await make_category(categories, user_id, CategoryType.EXPENSE)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=currency.id),
        )
        client.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=expense.id, currency_id=currency.id),
        )

        response = client.get("/api/transactions", params={"type": "income"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category_id"] == str(income.id)

    async def test_filter_by_date_range(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        )
        client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        )

        response = client.get(
            "/api/transactions", params={"date_from": "2025-12-01T00:00:00Z", "date_to": "2026-02-01T00:00:00Z"}
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_invalid_date_range_returns_400(self) -> None:
        client = make_client()

        response = client.get(
            "/api/transactions", params={"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"}
        )

        assert response.status_code == 400

    async def test_list_sorted_by_occurred_at_desc(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_id)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        early = client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        ).json()
        late = client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        ).json()

        response = client.get("/api/transactions")

        ids = [item["id"] for item in response.json()["items"]]
        assert ids == [late["id"], early["id"]]

    async def test_default_pagination(self) -> None:
        client = make_client()

        response = client.get("/api/transactions")

        assert response.status_code == 200
        assert response.json()["limit"] == 20
        assert response.json()["offset"] == 0

    async def test_invalid_pagination_params_rejected(self) -> None:
        client = make_client()

        assert client.get("/api/transactions", params={"limit": 0}).status_code == 400
        assert client.get("/api/transactions", params={"limit": 101}).status_code == 400
        assert client.get("/api/transactions", params={"offset": -1}).status_code == 400


class TestUserIsolation:
    async def test_foreign_transaction_is_not_readable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_b)
        transaction_id = client_a.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.get(f"/api/transactions/{transaction_id}")

        assert response.status_code == 404

    async def test_foreign_transaction_is_not_updatable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_b)
        transaction_id = client_a.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.put(
            f"/api/transactions/{transaction_id}",
            json=transaction_payload(
                wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="1.00"
            ),
        )

        assert response.status_code == 404
        assert client_a.get(f"/api/transactions/{transaction_id}").json()["amount"] == "100.00"

    async def test_foreign_transaction_is_not_deletable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_b)
        transaction_id = client_a.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.delete(f"/api/transactions/{transaction_id}")

        assert response.status_code == 404
        assert client_a.get(f"/api/transactions/{transaction_id}").status_code == 200

    async def test_list_does_not_contain_other_users_transactions(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_b)
        client_a.post(
            "/api/transactions",
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        )

        response = client_b.get("/api/transactions")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0


class TestWalletBalances:
    async def test_balance_zero_without_transactions(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, _, currency = await make_environment(user_id)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

        response = client.get(f"/api/wallets/{wallet.id}/balances")

        assert response.status_code == 200
        assert response.json() == [{"currency_id": str(currency.id), "balance": "0"}]

    async def test_balance_reflects_income_and_expense(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, income, currency = await make_environment(user_id)
        expense = await make_category(categories, user_id, CategoryType.EXPENSE)
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id, category_id=income.id, currency_id=currency.id, amount="100.00"
            ),
        )
        client.post(
            "/api/transactions",
            json=transaction_payload(
                wallet_id=wallet.id, category_id=expense.id, currency_id=currency.id, amount="30.00"
            ),
        )

        response = client.get(f"/api/wallets/{wallet.id}/balances")

        assert response.status_code == 200
        assert response.json() == [{"currency_id": str(currency.id), "balance": "70.00"}]

    async def test_balance_separates_currencies_for_multicurrency_wallet(self) -> None:
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

    async def test_balance_unknown_or_foreign_wallet_returns_404(self) -> None:
        user_id = uuid4()
        wallets, categories, currencies, wallet, _, _ = await make_environment(uuid4())
        client = make_client(wallets=wallets, categories=categories, currencies=currencies, user_id=user_id)

        assert client.get(f"/api/wallets/{uuid4()}/balances").status_code == 404
        assert client.get(f"/api/wallets/{wallet.id}/balances").status_code == 404
