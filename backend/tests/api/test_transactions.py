from datetime import UTC, datetime
from decimal import Decimal
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
    workspaces.seed(
        Workspace(
            id=workspace_id,
            user_id=user_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            name="Т",
            currency_id=uuid4(),
        )
    )
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


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id: UUID, currency_id: UUID) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_id=currency_id,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def make_category(
    categories: InMemoryCategoryRepository,
    workspace_id: UUID,
    type: CategoryType = CategoryType.EXPENSE,
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
    amount: str = "100.00",
    occurred_at: str | None = None,
    comment: str | None = None,
) -> dict:
    payload = {
        "wallet_id": str(wallet_id),
        "category_id": str(category_id),
        "amount": amount,
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    if comment is not None:
        payload["comment"] = comment
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
    wallet = await make_wallet(wallets, workspace_id, currency.id)
    category = await make_category(categories, workspace_id, CategoryType.EXPENSE)
    return wallets, categories, currencies, wallet, category, currency


async def test_create_transaction_with_explicit_date() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, occurred_at="2026-03-01T12:00:00"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_id"] == str(wallet.id)
    assert body["category_id"] == str(category.id)
    assert body["legs"] == [{"currency_id": str(currency.id), "amount": "100.00"}]
    assert body["occurred_at"] == "2026-03-01T12:00:00"
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
    )

    assert response.status_code == 201
    assert response.json()["occurred_at"] is not None


async def test_create_transaction_rejects_currency_in_request() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json={**transaction_payload(wallet_id=wallet.id, category_id=category.id), "currency_id": str(currency.id)},
    )

    assert response.status_code == 400


async def test_create_transaction_uses_wallet_currency() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, _, category, _ = await make_environment(workspace_id)
    cny = await make_currency(currencies, "CNY")
    cny_wallet = await make_wallet(wallets, workspace_id, cny.id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=cny_wallet.id, category_id=category.id, amount="12.50"),
    )

    assert response.status_code == 201
    assert response.json()["legs"] == [{"currency_id": str(cny.id), "amount": "12.50"}]


async def test_create_transaction_checks_precision_by_wallet_currency() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, _, category, _ = await make_environment(workspace_id)
    jpy = await make_currency(currencies, "JPY", decimal_places=0)
    jpy_wallet = await make_wallet(wallets, workspace_id, jpy.id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=jpy_wallet.id, category_id=category.id, amount="10.5"),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, amount="1.005"),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, amount="0"),
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
        json=transaction_payload(wallet_id=uuid4(), category_id=category.id),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=uuid4()),
    )

    assert response.status_code == 404


async def test_create_transaction_rejects_foreign_category() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(uuid4())
    wallets2 = InMemoryWalletRepository()
    own_wallet = await make_wallet(wallets2, workspace_id, currency.id)
    client, workspace_id = make_client(
        wallets=wallets2, categories=categories, currencies=currencies, workspace_id=workspace_id
    )

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=own_wallet.id, category_id=category.id),
    )

    assert response.status_code == 404


async def test_create_transaction_without_session_is_401() -> None:
    client, workspace_id = make_client(authenticated=False)

    response = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=uuid4(), category_id=uuid4()),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=other_category.id, amount="55.00"),
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
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
    )

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    workspace_id = uuid4()
    wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(
        wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
    )
    transaction_id = client.post(
        transactions_url(workspace_id),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
    ).json()["id"]

    currency_response = client.put(
        transactions_url(workspace_id, f"/{transaction_id}"),
        json={**transaction_payload(wallet_id=wallet.id, category_id=category.id), "currency_id": str(currency.id)},
    )
    assert currency_response.status_code == 400

    amount_response = client.put(
        transactions_url(workspace_id, f"/{transaction_id}"),
        json=transaction_payload(wallet_id=wallet.id, category_id=category.id, amount="0"),
    )
    assert amount_response.status_code == 400


async def test_delete_unknown_transaction_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.delete(transactions_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


class TestFiltersAndSorting:
    async def test_filter_by_wallet(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet_a, category, currency = await make_environment(workspace_id)
        wallet_b = await make_wallet(wallets, workspace_id, currency.id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet_a.id, category_id=category.id),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet_b.id, category_id=category.id),
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
            json=transaction_payload(wallet_id=wallet.id, category_id=category_a.id),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category_b.id),
        )

        response = client.get(transactions_url(workspace_id), params={"category_id": str(category_a.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category_id"] == str(category_a.id)

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
                occurred_at="2026-01-01T00:00:00",
            ),
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                occurred_at="2026-06-01T00:00:00",
            ),
        )

        response = client.get(
            transactions_url(workspace_id),
            params={"date_from": "2025-12-01T00:00:00", "date_to": "2026-02-01T00:00:00"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_invalid_date_range_returns_400(self) -> None:
        client, workspace_id = make_client()

        response = client.get(
            transactions_url(workspace_id),
            params={"date_from": "2026-02-01T00:00:00", "date_to": "2026-01-01T00:00:00"},
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
                occurred_at="2026-01-01T00:00:00",
            ),
        ).json()
        late = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(
                wallet_id=wallet.id,
                category_id=category.id,
                occurred_at="2026-06-01T00:00:00",
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
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
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
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
        ).json()["id"]

        response = client_b.put(
            transactions_url(workspace_b, f"/{transaction_id}"),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, amount="1.00"),
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
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
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
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
        )

        response = client_b.get(transactions_url(workspace_b))

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0


class TestComments:
    async def test_create_with_comment(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, comment="Серый рюкзак"),
        )

        assert response.status_code == 201
        assert response.json()["comment"] == "Серый рюкзак"

    async def test_create_without_comment_is_null(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
        )

        assert response.status_code == 201
        assert response.json()["comment"] is None

    async def test_whitespace_comment_is_normalized_to_null(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, comment="   "),
        )

        assert response.status_code == 201
        assert response.json()["comment"] is None

    async def test_too_long_comment_is_rejected(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, comment="x" * 1001),
        )

        assert response.status_code == 400

    async def test_put_changes_and_clears_comment(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        created = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, comment="Исходный"),
        ).json()
        transaction_id = created["id"]

        changed = client.put(
            transactions_url(workspace_id, f"/{transaction_id}"),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id, comment="Новый"),
        )
        assert changed.status_code == 200
        assert changed.json()["comment"] == "Новый"

        cleared = client.put(
            transactions_url(workspace_id, f"/{transaction_id}"),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
        )
        assert cleared.status_code == 200
        assert cleared.json()["comment"] is None


class TestTopupsAreSeparate:
    async def test_create_rejects_income_category(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, _, currency = await make_environment(workspace_id)
        income = await make_category(categories, workspace_id, CategoryType.INCOME)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )

        response = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=income.id),
        )

        assert response.status_code == 400

    async def test_put_rejects_income_category(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, category, currency = await make_environment(workspace_id)
        income = await make_category(categories, workspace_id, CategoryType.INCOME)
        client, workspace_id = make_client(
            wallets=wallets, categories=categories, currencies=currencies, workspace_id=workspace_id
        )
        transaction_id = client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=category.id),
        ).json()["id"]

        response = client.put(
            transactions_url(workspace_id, f"/{transaction_id}"),
            json=transaction_payload(wallet_id=wallet.id, category_id=income.id),
        )

        assert response.status_code == 400

    async def test_old_topups_route_is_gone(self) -> None:
        client, workspace_id = make_client()

        response = client.post(transactions_url(workspace_id, "/topups"), json={})

        assert response.status_code != 201

    async def test_list_get_put_delete_do_not_touch_topups(self) -> None:
        workspace_id = uuid4()
        wallets, categories, currencies, wallet, expense, currency = await make_environment(workspace_id)
        income = await make_category(categories, workspace_id, CategoryType.INCOME)
        transactions = InMemoryTransactionRepository(categories)
        topup = await transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                category_id=income.id,
                legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("5")),),
                occurred_at=datetime(2026, 1, 1),
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        client, workspace_id = make_client(
            wallets=wallets,
            categories=categories,
            currencies=currencies,
            transactions=transactions,
            workspace_id=workspace_id,
        )
        client.post(
            transactions_url(workspace_id),
            json=transaction_payload(wallet_id=wallet.id, category_id=expense.id),
        )

        listing = client.get(transactions_url(workspace_id))
        read = client.get(transactions_url(workspace_id, f"/{topup.id}"))
        put = client.put(
            transactions_url(workspace_id, f"/{topup.id}"),
            json=transaction_payload(wallet_id=wallet.id, category_id=expense.id),
        )
        delete = client.delete(transactions_url(workspace_id, f"/{topup.id}"))

        assert listing.json()["total"] == 1
        assert listing.json()["items"][0]["category_id"] == str(expense.id)
        assert read.status_code == 404
        assert put.status_code == 404
        assert delete.status_code == 404
        assert await transactions.get_by_id(topup.id, workspace_id) is not None
