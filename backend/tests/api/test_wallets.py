from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Transaction
from core.exceptions import ConflictError
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
    currencies: InMemoryCurrencyRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app)


async def seeded_currencies() -> tuple[InMemoryCurrencyRepository, Currency, Currency]:
    repo = InMemoryCurrencyRepository()
    rub = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
    cny = Currency(id=uuid4(), code="CNY", name="Китайский юань", decimal_places=2)
    await repo.upsert_many([rub, cny])
    return repo, rub, cny


def wallet_payload(currency_ids: list[UUID], name: str = "Наличные", icon: str = "wallet") -> dict:
    return {"name": name, "icon": icon, "currency_ids": [str(cid) for cid in currency_ids]}


async def test_create_wallet_with_one_currency() -> None:
    currencies, rub, _ = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.post("/api/wallets", json=wallet_payload([rub.id]))

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Наличные"
    assert body["icon"] == "wallet"
    assert body["currency_ids"] == [str(rub.id)]
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_wallet_with_multiple_currencies() -> None:
    currencies, rub, cny = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.post("/api/wallets", json=wallet_payload([rub.id, cny.id]))

    assert response.status_code == 201
    assert set(response.json()["currency_ids"]) == {str(rub.id), str(cny.id)}


async def test_create_wallet_rejects_empty_name() -> None:
    currencies, rub, _ = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.post("/api/wallets", json=wallet_payload([rub.id], name="   "))

    assert response.status_code == 400


async def test_create_wallet_rejects_unknown_icon() -> None:
    currencies, rub, _ = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.post("/api/wallets", json=wallet_payload([rub.id], icon="not-an-icon"))

    assert response.status_code == 400


async def test_create_wallet_rejects_empty_currency_ids() -> None:
    client = make_client()

    response = client.post("/api/wallets", json=wallet_payload([]))

    assert response.status_code == 400


async def test_create_wallet_rejects_duplicate_currency_ids() -> None:
    currencies, rub, _ = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.post("/api/wallets", json=wallet_payload([rub.id, rub.id]))

    assert response.status_code == 400


async def test_create_wallet_rejects_unknown_currency() -> None:
    unknown_id = uuid4()
    client = make_client()

    response = client.post("/api/wallets", json=wallet_payload([unknown_id]))

    assert response.status_code == 400
    assert str(unknown_id) in response.json()["detail"]


async def test_create_wallet_without_session_is_401() -> None:
    client = make_client(authenticated=False)

    response = client.post("/api/wallets", json=wallet_payload([uuid4()]))

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    currencies, rub, cny = await seeded_currencies()
    wallets = InMemoryWalletRepository()
    client = make_client(wallets=wallets, currencies=currencies)

    created = client.post("/api/wallets", json=wallet_payload([rub.id])).json()
    wallet_id = created["id"]

    got = client.get(f"/api/wallets/{wallet_id}")
    assert got.status_code == 200
    assert got.json()["id"] == wallet_id

    listed = client.get("/api/wallets")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == wallet_id

    updated = client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([cny.id], name="Обновлённый"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Обновлённый"
    assert updated.json()["currency_ids"] == [str(cny.id)]
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(f"/api/wallets/{wallet_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/wallets/{wallet_id}")
    assert after_delete.status_code == 404


async def test_get_unknown_wallet_returns_404() -> None:
    client = make_client()

    response = client.get(f"/api/wallets/{uuid4()}")

    assert response.status_code == 404


async def test_put_unknown_wallet_returns_404() -> None:
    currencies, rub, _ = await seeded_currencies()
    client = make_client(currencies=currencies)

    response = client.put(f"/api/wallets/{uuid4()}", json=wallet_payload([rub.id]))

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    currencies, rub, _ = await seeded_currencies()
    wallets = InMemoryWalletRepository()
    client = make_client(wallets=wallets, currencies=currencies)
    wallet_id = client.post("/api/wallets", json=wallet_payload([rub.id])).json()["id"]

    assert client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([rub.id], name=" ")).status_code == 400
    assert client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([rub.id], icon="nope")).status_code == 400
    assert client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([])).status_code == 400
    assert client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([rub.id, rub.id])).status_code == 400
    unknown_id = uuid4()
    assert client.put(f"/api/wallets/{wallet_id}", json=wallet_payload([unknown_id])).status_code == 400


async def test_delete_unknown_wallet_returns_404() -> None:
    client = make_client()

    response = client.delete(f"/api/wallets/{uuid4()}")

    assert response.status_code == 404


class RestrictingWalletRepository(InMemoryWalletRepository):
    """Симулирует `ON DELETE RESTRICT` `transactions.wallet_id` (реальный `WalletRepository` перехватывает
    `IntegrityError` и поднимает `ConflictError` — см. design.md `transactions`)."""

    def __init__(self, transactions: InMemoryTransactionRepository) -> None:
        super().__init__()
        self._transaction_repo = transactions

    async def delete(self, wallet_id: UUID, user_id: UUID) -> bool:
        if await self._transaction_repo.references_wallet(wallet_id):
            raise ConflictError("Кошелёк нельзя удалить: есть операции")
        return await super().delete(wallet_id, user_id)


async def test_delete_wallet_with_transactions_returns_409() -> None:
    currencies, rub, _ = await seeded_currencies()
    categories = InMemoryCategoryRepository()
    transactions = InMemoryTransactionRepository(categories)
    wallets = RestrictingWalletRepository(transactions)
    user_id = uuid4()
    client = make_client(
        wallets=wallets, currencies=currencies, categories=categories, transactions=transactions, user_id=user_id
    )
    wallet_id = client.post("/api/wallets", json=wallet_payload([rub.id])).json()["id"]
    category = await categories.add(
        Category(
            id=uuid4(),
            user_id=user_id,
            type=CategoryType.INCOME,
            name="Зарплата",
            icon="wallet",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    transaction = await transactions.add(
        Transaction(
            id=uuid4(),
            user_id=user_id,
            wallet_id=UUID(wallet_id),
            category_id=category.id,
            currency_id=rub.id,
            amount=Decimal("10"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    response = client.delete(f"/api/wallets/{wallet_id}")

    assert response.status_code == 409
    assert client.get(f"/api/wallets/{wallet_id}").status_code == 200
    assert await transactions.get_by_id(transaction.id, user_id) is not None


class TestUserIsolation:
    async def test_foreign_wallet_is_not_readable(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        wallet_id = client_a.post("/api/wallets", json=wallet_payload([rub.id])).json()["id"]

        response = client_b.get(f"/api/wallets/{wallet_id}")

        assert response.status_code == 404

    async def test_foreign_wallet_is_not_updatable(self) -> None:
        currencies, rub, cny = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        wallet_id = client_a.post("/api/wallets", json=wallet_payload([rub.id])).json()["id"]

        response = client_b.put(f"/api/wallets/{wallet_id}", json=wallet_payload([cny.id], name="Чужое"))

        assert response.status_code == 404
        assert client_a.get(f"/api/wallets/{wallet_id}").json()["name"] == "Наличные"

    async def test_foreign_wallet_is_not_deletable(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        wallet_id = client_a.post("/api/wallets", json=wallet_payload([rub.id])).json()["id"]

        response = client_b.delete(f"/api/wallets/{wallet_id}")

        assert response.status_code == 404
        assert client_a.get(f"/api/wallets/{wallet_id}").status_code == 200

    async def test_list_does_not_contain_other_users_wallets(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        client_a.post("/api/wallets", json=wallet_payload([rub.id], name="Кошелёк A"))

        response = client_b.get("/api/wallets")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0
