from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Currency, Transaction, TransactionLeg, Wallet, Workspace
from core.exceptions import ConflictError
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
    categories: InMemoryCategoryRepository | None = None,
    wallets: InMemoryWalletRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    categories = categories if categories is not None else InMemoryCategoryRepository()
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    workspaces = workspaces if workspaces is not None else InMemoryWorkspaceRepository()
    user_id = user_id if user_id is not None else uuid4()
    workspace_id = workspace_id if workspace_id is not None else uuid4()
    workspaces.seed(Workspace(id=workspace_id, user_id=user_id, created_at=datetime(2026, 1, 1, tzinfo=UTC), name="Т"))
    app = create_app()
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), workspace_id


def categories_url(workspace_id: UUID, suffix: str = "") -> str:
    return f"/api/workspaces/{workspace_id}/categories{suffix}"


def category_payload(type: str = "income", name: str = "Зарплата", icon: str = "wallet") -> dict:
    return {"type": type, "name": name, "icon": icon}


async def test_create_income_category() -> None:
    client, workspace_id = make_client()

    response = client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "income"
    assert body["name"] == "Зарплата"
    assert body["icon"] == "wallet"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_expense_category() -> None:
    client, workspace_id = make_client()

    response = client.post(categories_url(workspace_id), json=category_payload(type="expense", name="Продукты"))

    assert response.status_code == 201
    assert response.json()["type"] == "expense"


async def test_create_category_rejects_empty_name() -> None:
    client, workspace_id = make_client()

    response = client.post(categories_url(workspace_id), json=category_payload(name="   "))

    assert response.status_code == 400


async def test_create_category_rejects_unknown_icon() -> None:
    client, workspace_id = make_client()

    response = client.post(categories_url(workspace_id), json=category_payload(icon="not-an-icon"))

    assert response.status_code == 400


async def test_create_category_rejects_invalid_type() -> None:
    client, workspace_id = make_client()

    response = client.post(categories_url(workspace_id), json=category_payload(type="savings"))

    assert response.status_code == 400


async def test_create_category_duplicate_name_within_type_is_409() -> None:
    categories = InMemoryCategoryRepository()
    client, workspace_id = make_client(categories=categories)
    client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))

    response = client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))

    assert response.status_code == 409


async def test_create_category_same_name_different_type_is_allowed() -> None:
    categories = InMemoryCategoryRepository()
    client, workspace_id = make_client(categories=categories)
    client.post(categories_url(workspace_id), json=category_payload(type="income", name="Прочее"))

    response = client.post(categories_url(workspace_id), json=category_payload(type="expense", name="Прочее"))

    assert response.status_code == 201


async def test_create_category_without_session_is_401() -> None:
    client, workspace_id = make_client(authenticated=False)

    response = client.post(categories_url(workspace_id), json=category_payload())

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    categories = InMemoryCategoryRepository()
    client, workspace_id = make_client(categories=categories)

    created = client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата")).json()
    category_id = created["id"]

    got = client.get(categories_url(workspace_id, f"/{category_id}"))
    assert got.status_code == 200
    assert got.json()["id"] == category_id

    listed = client.get(categories_url(workspace_id))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == category_id

    updated = client.put(
        categories_url(workspace_id, f"/{category_id}"), json=category_payload(type="expense", name="Обновлённая")
    )
    assert updated.status_code == 200
    assert updated.json()["type"] == "expense"
    assert updated.json()["name"] == "Обновлённая"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(categories_url(workspace_id, f"/{category_id}"))
    assert deleted.status_code == 204

    after_delete = client.get(categories_url(workspace_id, f"/{category_id}"))
    assert after_delete.status_code == 404


async def test_get_unknown_category_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.get(categories_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


async def test_put_unknown_category_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.put(categories_url(workspace_id, f"/{uuid4()}"), json=category_payload())

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    categories = InMemoryCategoryRepository()
    client, workspace_id = make_client(categories=categories)
    category_id = client.post(categories_url(workspace_id), json=category_payload()).json()["id"]
    url = categories_url(workspace_id, f"/{category_id}")

    assert client.put(url, json=category_payload(name=" ")).status_code == 400
    assert client.put(url, json=category_payload(icon="nope")).status_code == 400
    assert client.put(url, json=category_payload(type="nope")).status_code == 400


async def test_put_duplicate_name_conflict() -> None:
    categories = InMemoryCategoryRepository()
    client, workspace_id = make_client(categories=categories)
    client.post(categories_url(workspace_id), json=category_payload(type="income", name="A"))
    category_b_id = client.post(categories_url(workspace_id), json=category_payload(type="income", name="B")).json()[
        "id"
    ]

    response = client.put(
        categories_url(workspace_id, f"/{category_b_id}"), json=category_payload(type="income", name="A")
    )

    assert response.status_code == 409


async def test_delete_unknown_category_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.delete(categories_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


class RestrictingCategoryRepository(InMemoryCategoryRepository):
    """Симулирует `ON DELETE RESTRICT` `transactions.category_id` (реальный `CategoryRepository` перехватывает
    `IntegrityError` и поднимает `ConflictError` — см. design.md `transactions`)."""

    def __init__(self, transactions: InMemoryTransactionRepository) -> None:
        super().__init__()
        self._transaction_repo = transactions

    async def delete(self, category_id: UUID, workspace_id: UUID) -> bool:
        if await self._transaction_repo.references_category(category_id):
            raise ConflictError("Категорию нельзя удалить: есть операции")
        return await super().delete(category_id, workspace_id)


async def test_delete_category_with_transactions_returns_409() -> None:
    # `InMemoryTransactionRepository` нужна ссылка на категории для чтения `type` (см. её докстринг); тест не
    # фильтрует по типу, поэтому отдельный пустой репозиторий категорий для этой цели достаточен.
    transactions = InMemoryTransactionRepository(InMemoryCategoryRepository())
    categories = RestrictingCategoryRepository(transactions)
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    client, workspace_id = make_client(
        categories=categories, wallets=wallets, currencies=currencies, transactions=transactions
    )
    category_id = client.post(categories_url(workspace_id), json=category_payload()).json()["id"]
    currency = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
    await currencies.upsert_many([currency])
    wallet = await wallets.add(
        Wallet(
            id=uuid4(),
            workspace_id=workspace_id,
            name="Кошелёк",
            icon="wallet",
            currency_ids=(currency.id,),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    transaction = await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            category_id=UUID(category_id),
            legs=(TransactionLeg(currency_id=currency.id, amount=Decimal("10")),),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    response = client.delete(categories_url(workspace_id, f"/{category_id}"))

    assert response.status_code == 409
    assert client.get(categories_url(workspace_id, f"/{category_id}")).status_code == 200
    assert await transactions.get_by_id(transaction.id, workspace_id) is not None


class TestTypeFilter:
    async def test_filter_by_income(self) -> None:
        categories = InMemoryCategoryRepository()
        client, workspace_id = make_client(categories=categories)
        client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))
        client.post(categories_url(workspace_id), json=category_payload(type="expense", name="Продукты"))

        response = client.get(categories_url(workspace_id), params={"type": "income"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "income"

    async def test_filter_by_expense(self) -> None:
        categories = InMemoryCategoryRepository()
        client, workspace_id = make_client(categories=categories)
        client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))
        client.post(categories_url(workspace_id), json=category_payload(type="expense", name="Продукты"))

        response = client.get(categories_url(workspace_id), params={"type": "expense"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "expense"

    async def test_without_filter_returns_both_types(self) -> None:
        categories = InMemoryCategoryRepository()
        client, workspace_id = make_client(categories=categories)
        client.post(categories_url(workspace_id), json=category_payload(type="income", name="Зарплата"))
        client.post(categories_url(workspace_id), json=category_payload(type="expense", name="Продукты"))

        response = client.get(categories_url(workspace_id))

        assert response.status_code == 200
        assert response.json()["total"] == 2


class TestWorkspaceIsolation:
    async def test_foreign_category_is_not_readable(self) -> None:
        categories = InMemoryCategoryRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(categories=categories, workspaces=workspaces)
        client_b, workspace_b = make_client(categories=categories, workspaces=workspaces)
        category_id = client_a.post(categories_url(workspace_a), json=category_payload()).json()["id"]

        response = client_b.get(categories_url(workspace_b, f"/{category_id}"))

        assert response.status_code == 404

    async def test_foreign_category_is_not_updatable(self) -> None:
        categories = InMemoryCategoryRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(categories=categories, workspaces=workspaces)
        client_b, workspace_b = make_client(categories=categories, workspaces=workspaces)
        category_id = client_a.post(categories_url(workspace_a), json=category_payload(name="Зарплата")).json()["id"]

        response = client_b.put(categories_url(workspace_b, f"/{category_id}"), json=category_payload(name="Чужое"))

        assert response.status_code == 404
        assert client_a.get(categories_url(workspace_a, f"/{category_id}")).json()["name"] == "Зарплата"

    async def test_foreign_category_is_not_deletable(self) -> None:
        categories = InMemoryCategoryRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(categories=categories, workspaces=workspaces)
        client_b, workspace_b = make_client(categories=categories, workspaces=workspaces)
        category_id = client_a.post(categories_url(workspace_a), json=category_payload()).json()["id"]

        response = client_b.delete(categories_url(workspace_b, f"/{category_id}"))

        assert response.status_code == 404
        assert client_a.get(categories_url(workspace_a, f"/{category_id}")).status_code == 200

    async def test_list_does_not_contain_other_workspaces_categories(self) -> None:
        categories = InMemoryCategoryRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(categories=categories, workspaces=workspaces)
        client_b, workspace_b = make_client(categories=categories, workspaces=workspaces)
        client_a.post(categories_url(workspace_a), json=category_payload(name="Категория A"))

        response = client_b.get(categories_url(workspace_b))

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_same_name_same_type_does_not_conflict_between_workspaces(self) -> None:
        categories = InMemoryCategoryRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(categories=categories, workspaces=workspaces)
        client_b, workspace_b = make_client(categories=categories, workspaces=workspaces)
        client_a.post(categories_url(workspace_a), json=category_payload(type="income", name="Зарплата"))

        response = client_b.post(categories_url(workspace_b), json=category_payload(type="income", name="Зарплата"))

        assert response.status_code == 201

    async def test_using_foreign_workspace_id_in_path_is_404(self) -> None:
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(workspaces=workspaces)
        client_b, _ = make_client(workspaces=workspaces)

        response = client_b.get(categories_url(workspace_a))

        assert response.status_code == 404
