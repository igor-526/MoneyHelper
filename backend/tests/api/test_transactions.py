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


def transactions_url(workspace_id: UUID, suffix: str = "") -> str:
    return f"/api/workspaces/{workspace_id}/transactions{suffix}"


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


def topup_payload(
    *,
    wallet_id: UUID,
    category_id: UUID,
    legs: list[dict],
    occurred_at: str | None = None,
) -> dict:
    payload: dict = {"wallet_id": str(wallet_id), "category_id": str(category_id), "legs": legs}
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return payload


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


async def test_create_transaction_with_explicit_date() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(
            wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, occurred_at="2026-03-01T12:00:00Z"
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_id"] == str(wallet.id)
    assert body["category_id"] == str(category.id)
    assert body["legs"] == [{"currency_id": str(currency.id), "amount": "100.00"}]
    assert body["occurred_at"] == "2026-03-01T12:00:00Z"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_transaction_without_date_uses_server_time() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 201
    assert response.json()["occurred_at"] is not None


async def test_create_transaction_rejects_currency_not_in_wallet() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, _ = await make_environment(workspace_id)
    other_currency = await make_currency(currencies, "CNY")
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=other_currency.id),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_amount_exceeding_decimal_places() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(
            wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="1.005"
        ),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_nonpositive_amount() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="0"),
    )

    assert response.status_code == 400


async def test_create_transaction_rejects_unknown_wallet() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, _, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=uuid4(), category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_foreign_wallet() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(uuid4())
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_unknown_category() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, _, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=uuid4(), currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_foreign_category() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(uuid4())
    wallets2 = InMemoryWalletRepository()
    own_wallet = await make_wallet(wallets2, workspace_id, [currency.id])
    client, workspace_id = make_client(
        wallets=wallets2, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=own_wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transaction_without_session_is_401() -> None:
    client, workspace_id = make_client(authenticated=False)

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=uuid4(), category_id=uuid4(), currency_id=uuid4()),
    )

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    other_category = await make_category(categories, workspace_id, CategoryType.EXPENSE)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    created = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    ).json()
    transaction_id = created["id"]

    got = client.get(transactions_url(workspace_id, f"/{transaction_id}"))
    assert got.status_code == 200
    assert got.json()["id"] == transaction_id

    listed = client.get(transactions_url(workspace_id))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == transaction_id

    updated = client.put(
        transactions_url(workspace_id, f"/{transaction_id}"),
        json=transaction_payload(
            wallet_id=wallet.id, category_id=other_category.id, currency_id=currency.id, amount="55.00"
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["category_id"] == str(other_category.id)
    assert updated.json()["legs"] == [{"currency_id": str(currency.id), "amount": "55.00"}]
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(transactions_url(workspace_id, f"/{transaction_id}"))
    assert deleted.status_code == 204

    after_delete = client.get(transactions_url(workspace_id, f"/{transaction_id}"))
    assert after_delete.status_code == 404


async def test_get_unknown_transaction_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.get(transactions_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


async def test_put_unknown_transaction_returns_404() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.put(
        transactions_url(workspace_id, f"/{uuid4()}"),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    other_currency = await make_currency(currencies, "CNY")
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    transaction_id = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
    ).json()["id"]

    currency_response = client.put(
        transactions_url(workspace_id, f"/{transaction_id}"),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=other_currency.id),
    )
    assert currency_response.status_code == 400

    amount_response = client.put(
        transactions_url(workspace_id, f"/{transaction_id}"),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="0"),
    )
    assert amount_response.status_code == 400


async def test_put_on_topup_replaces_multiple_legs_with_one() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, rub = await make_environment(workspace_id)
    cny = await make_currency(currencies, "CNY")
    multi_wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    topup_id = client.post(
        transactions_url(workspace_id, "/topups"),
        json=topup_payload(
            wallet_id=multi_wallet.id,
            category_id=category.id,
            legs=[
                {"currency_id": str(rub.id), "amount": "10000.00"},
                {"currency_id": str(cny.id), "amount": "780.00"},
            ],
        ),
    ).json()["id"]

    response = client.put(
        transactions_url(workspace_id, f"/{topup_id}"),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=rub.id, amount="1.00"),
    )

    assert response.status_code == 200
    assert response.json()["legs"] == [{"currency_id": str(rub.id), "amount": "1.00"}]


async def test_delete_unknown_transaction_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.delete(transactions_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


class TestFiltersAndSorting:
    async def test_filter_by_wallet(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet_a, category, currency = await make_environment(workspace_id)
        wallet_b = await make_wallet(wallets, workspace_id, [currency.id])
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet_a.id, category_id=category.id, currency_id=currency.id),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet_b.id, category_id=category.id, currency_id=currency.id),
        )

        response = client.get(transactions_url(workspace_id), params={"wallet_id": str(wallet_a.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["wallet_id"] == str(wallet_a.id)

    async def test_filter_by_category(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category_a, currency = await make_environment(workspace_id)
        category_b = await make_category(categories, workspace_id, CategoryType.EXPENSE)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category_a.id, currency_id=currency.id),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category_b.id, currency_id=currency.id),
        )

        response = client.get(transactions_url(workspace_id), params={"category_id": str(category_a.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category_id"] == str(category_a.id)

    async def test_filter_by_type(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, income, currency = await make_environment(workspace_id)
        expense = await make_category(categories, workspace_id, CategoryType.EXPENSE)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=income.id, currency_id=currency.id),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=expense.id, currency_id=currency.id),
        )

        response = client.get(transactions_url(workspace_id), params={"type": "income"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category_id"] == str(income.id)

    async def test_filter_by_date_range(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        )

        response = client.get(
            transactions_url(workspace_id),
            params={"date_from": "2025-12-01T00:00:00Z", "date_to": "2026-02-01T00:00:00Z"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_invalid_date_range_returns_400(self) -> None:
        client, workspace_id = make_client()

        response = client.get(
            transactions_url(workspace_id),
            params={"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
        )

        assert response.status_code == 400

    async def test_list_sorted_by_occurred_at_desc(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        early = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        ).json()
        late = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        ).json()

        response = client.get(transactions_url(workspace_id))

        ids = [item["id"] for item in response.json()["items"]]
        assert ids == [late["id"], early["id"]]

    async def test_default_pagination(self) -> None:
        client, workspace_id = make_client()

        response = client.get(transactions_url(workspace_id))

        assert response.status_code == 200
        assert response.json()["limit"] == 20
        assert response.json()["offset"] == 0

    async def test_invalid_pagination_params_rejected(self) -> None:
        client, workspace_id = make_client()

        assert client.get(transactions_url(workspace_id), params={"limit": 0}).status_code == 400
        assert client.get(transactions_url(workspace_id), params={"limit": 101}).status_code == 400
        assert client.get(transactions_url(workspace_id), params={"offset": -1}).status_code == 400

    async def test_list_shows_topup_with_multiple_legs(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, _, category, rub = await make_environment(workspace_id)
        cny = await make_currency(currencies, "CNY")
        wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[
                    {"currency_id": str(rub.id), "amount": "10000.00"},
                    {"currency_id": str(cny.id), "amount": "780.00"},
                ],
            ),
        )

        response = client.get(transactions_url(workspace_id))

        assert response.status_code == 200
        legs = response.json()["items"][0]["legs"]
        assert {leg["currency_id"] for leg in legs} == {str(rub.id), str(cny.id)}


class TestWorkspaceIsolation:
    async def test_foreign_transaction_is_not_readable(self) -> None:
        workspace_a = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets,
            categories=categories,
            currencies=currencies,
            workspaces=workspaces,
            workspace_id=workspace_a,
        )
        client_b, workspace_b = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspaces=workspaces
        )
        transaction_id = client_a.post(
            transactions_url(workspace_a),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.get(transactions_url(workspace_b, f"/{transaction_id}"))

        assert response.status_code == 404

    async def test_foreign_transaction_is_not_updatable(self) -> None:
        workspace_a = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets,
            categories=categories,
            currencies=currencies,
            workspaces=workspaces,
            workspace_id=workspace_a,
        )
        client_b, workspace_b = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspaces=workspaces
        )
        transaction_id = client_a.post(
            transactions_url(workspace_a),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.put(
            transactions_url(workspace_b, f"/{transaction_id}"),
            json=transaction_payload(
                wallet_id=wallet.id, category_id=category.id, currency_id=currency.id, amount="1.00"
            ),
        )

        assert response.status_code == 404
        assert (
            client_a.get(transactions_url(workspace_a, f"/{transaction_id}")).json()["legs"][0]["amount"] == "100.00"
        )

    async def test_foreign_transaction_is_not_deletable(self) -> None:
        workspace_a = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets,
            categories=categories,
            currencies=currencies,
            workspaces=workspaces,
            workspace_id=workspace_a,
        )
        client_b, workspace_b = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspaces=workspaces
        )
        transaction_id = client_a.post(
            transactions_url(workspace_a),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.delete(transactions_url(workspace_b, f"/{transaction_id}"))

        assert response.status_code == 404
        assert client_a.get(transactions_url(workspace_a, f"/{transaction_id}")).status_code == 200

    async def test_list_does_not_contain_other_workspaces_transactions(self) -> None:
        workspace_a = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets,
            categories=categories,
            currencies=currencies,
            workspaces=workspaces,
            workspace_id=workspace_a,
        )
        client_b, workspace_b = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspaces=workspaces
        )
        client_a.post(
            transactions_url(workspace_a),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, currency_id=currency.id),
        )

        response = client_b.get(transactions_url(workspace_b))

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0


class TestTopups:
    async def test_success_with_full_currency_set(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, _, category, rub = await make_environment(workspace_id)
        cny = await make_currency(currencies, "CNY")
        wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[
                    {"currency_id": str(rub.id), "amount": "10000.00"},
                    {"currency_id": str(cny.id), "amount": "780.00"},
                ],
                occurred_at="2026-03-01T12:00:00Z",
            ),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["wallet_id"] == str(wallet.id)
        assert body["category_id"] == str(category.id)
        assert {leg["currency_id"] for leg in body["legs"]} == {str(rub.id), str(cny.id)}
        assert body["occurred_at"] == "2026-03-01T12:00:00Z"

    async def test_without_date_uses_server_time(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id, category_id=category.id, legs=[{"currency_id": str(currency.id), "amount": "1"}]
            ),
        )

        assert response.status_code == 201
        assert response.json()["occurred_at"] is not None

    async def test_rate_is_reproducible_from_stored_legs(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, _, category, rub = await make_environment(workspace_id)
        cny = await make_currency(currencies, "CNY")
        wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[
                    {"currency_id": str(rub.id), "amount": "10000.00"},
                    {"currency_id": str(cny.id), "amount": "780.00"},
                ],
            ),
        )

        legs = {leg["currency_id"]: leg["amount"] for leg in response.json()["legs"]}
        rate = float(legs[str(rub.id)]) / float(legs[str(cny.id)])
        assert rate == float("10000.00") / float("780.00")

    async def test_rejects_incomplete_currency_set(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, _, category, rub = await make_environment(workspace_id)
        cny = await make_currency(currencies, "CNY")
        wallet = await make_wallet(wallets, workspace_id, [rub.id, cny.id])
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id, category_id=category.id, legs=[{"currency_id": str(rub.id), "amount": "100"}]
            ),
        )

        assert response.status_code == 400

    async def test_rejects_excessive_currency_set(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, rub = await make_environment(workspace_id)
        cny = await make_currency(currencies, "CNY")
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[
                    {"currency_id": str(rub.id), "amount": "100"},
                    {"currency_id": str(cny.id), "amount": "100"},
                ],
            ),
        )

        assert response.status_code == 400

    async def test_rejects_duplicate_currency_in_legs(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, rub = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[
                    {"currency_id": str(rub.id), "amount": "100"},
                    {"currency_id": str(rub.id), "amount": "50"},
                ],
            ),
        )

        assert response.status_code == 400

    async def test_rejects_non_income_category(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, _, currency = await make_environment(workspace_id)
        expense_category = await make_category(categories, workspace_id, CategoryType.EXPENSE)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=expense_category.id,
                legs=[{"currency_id": str(currency.id), "amount": "100"}],
            ),
        )

        assert response.status_code == 400

    async def test_rejects_nonpositive_leg_amount(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id, category_id=category.id, legs=[{"currency_id": str(currency.id), "amount": "0"}]
            ),
        )

        assert response.status_code == 400

    async def test_rejects_leg_amount_exceeding_decimal_places(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                legs=[{"currency_id": str(currency.id), "amount": "1.005"}],
            ),
        )

        assert response.status_code == 400

    async def test_rejects_unknown_wallet(self) -> None:
        workspace_id = uuid4()
        _, categories, currencies, _, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(categories=categories, currencies=currencies, workspace_id=workspace_id)

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=uuid4(), category_id=category.id, legs=[{"currency_id": str(currency.id), "amount": "1"}]
            ),
        )

        assert response.status_code == 404

    async def test_rejects_unknown_category(self) -> None:
        workspace_id = uuid4()
        wallets, _, currencies, wallet, _, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=wallet.id, category_id=uuid4(), legs=[{"currency_id": str(currency.id), "amount": "1"}]
            ),
        )

        assert response.status_code == 404

    async def test_without_session_is_401(self) -> None:
        client, workspace_id = make_client(authenticated=False)

        response = client.post(
            transactions_url(workspace_id, "/topups"),
            json=topup_payload(
                wallet_id=uuid4(), category_id=uuid4(), legs=[{"currency_id": str(uuid4()), "amount": "1"}]
            ),
        )

        assert response.status_code == 401

    async def test_topups_route_is_not_mistaken_for_transaction_id_route(self) -> None:
        client, workspace_id = make_client()

        # `POST /api/workspaces/{workspace_id}/transactions/topups` не эквивалентен несуществующему `POST
        # /api/workspaces/{workspace_id}/transactions/{transaction_id}` (у параметризованного маршрута нет метода
        # POST — 405/422, а не случайное совпадение с "topups", распознанным как `transaction_id`).
        response = client.get(transactions_url(workspace_id, "/topups"))

        assert response.status_code != 200
