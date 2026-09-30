from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Transfer, Workspace
from core.exceptions import ConflictError
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
    currencies: InMemoryCurrencyRepository | None = None,
    categories: InMemoryCategoryRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    transfers: InMemoryTransferRepository | None = None,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    categories = categories if categories is not None else InMemoryCategoryRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    transfers = transfers if transfers is not None else InMemoryTransferRepository()
    workspaces = workspaces if workspaces is not None else InMemoryWorkspaceRepository()
    user_id = user_id if user_id is not None else uuid4()
    workspace_id = workspace_id if workspace_id is not None else uuid4()
    workspaces.seed(Workspace(id=workspace_id, user_id=user_id, created_at=datetime(2026, 1, 1, tzinfo=UTC), name="Т"))
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_category_repository] = lambda: categories
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    app.dependency_overrides[get_transfer_repository] = lambda: transfers
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), workspace_id


def wallets_url(workspace_id: UUID, suffix: str = "") -> str:
    return f"/api/workspaces/{workspace_id}/wallets{suffix}"


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
    client, workspace_id = make_client(currencies=currencies)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id]))

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Наличные"
    assert body["icon"] == "wallet"
    assert body["currency_ids"] == [str(rub.id)]
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_wallet_with_multiple_currencies() -> None:
    currencies, rub, cny = await seeded_currencies()
    client, workspace_id = make_client(currencies=currencies)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id, cny.id]))

    assert response.status_code == 201
    assert set(response.json()["currency_ids"]) == {str(rub.id), str(cny.id)}


async def test_create_wallet_rejects_empty_name() -> None:
    currencies, rub, _ = await seeded_currencies()
    client, workspace_id = make_client(currencies=currencies)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id], name="   "))

    assert response.status_code == 400


async def test_create_wallet_rejects_unknown_icon() -> None:
    currencies, rub, _ = await seeded_currencies()
    client, workspace_id = make_client(currencies=currencies)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id], icon="not-an-icon"))

    assert response.status_code == 400


async def test_create_wallet_rejects_empty_currency_ids() -> None:
    client, workspace_id = make_client()

    response = client.post(wallets_url(workspace_id), json=wallet_payload([]))

    assert response.status_code == 400


async def test_create_wallet_rejects_duplicate_currency_ids() -> None:
    currencies, rub, _ = await seeded_currencies()
    client, workspace_id = make_client(currencies=currencies)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id, rub.id]))

    assert response.status_code == 400


async def test_create_wallet_rejects_unknown_currency() -> None:
    unknown_id = uuid4()
    client, workspace_id = make_client()

    response = client.post(wallets_url(workspace_id), json=wallet_payload([unknown_id]))

    assert response.status_code == 400
    assert str(unknown_id) in response.json()["detail"]


async def test_create_wallet_without_session_is_401() -> None:
    client, workspace_id = make_client(authenticated=False)

    response = client.post(wallets_url(workspace_id), json=wallet_payload([uuid4()]))

    assert response.status_code == 401


async def test_create_wallet_with_unknown_workspace_is_404() -> None:
    client, _ = make_client()

    response = client.post(wallets_url(uuid4()), json=wallet_payload([uuid4()]))

    assert response.status_code == 404


async def test_get_list_put_delete_full_cycle() -> None:
    currencies, rub, cny = await seeded_currencies()
    wallets = InMemoryWalletRepository()
    client, workspace_id = make_client(wallets=wallets, currencies=currencies)

    created = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id])).json()
    wallet_id = created["id"]

    got = client.get(wallets_url(workspace_id, f"/{wallet_id}"))
    assert got.status_code == 200
    assert got.json()["id"] == wallet_id

    listed = client.get(wallets_url(workspace_id))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == wallet_id

    updated = client.put(wallets_url(workspace_id, f"/{wallet_id}"), json=wallet_payload([cny.id], name="Обновлённый"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Обновлённый"
    assert updated.json()["currency_ids"] == [str(cny.id)]
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(wallets_url(workspace_id, f"/{wallet_id}"))
    assert deleted.status_code == 204

    after_delete = client.get(wallets_url(workspace_id, f"/{wallet_id}"))
    assert after_delete.status_code == 404


async def test_get_unknown_wallet_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.get(wallets_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


async def test_put_unknown_wallet_returns_404() -> None:
    currencies, rub, _ = await seeded_currencies()
    client, workspace_id = make_client(currencies=currencies)

    response = client.put(wallets_url(workspace_id, f"/{uuid4()}"), json=wallet_payload([rub.id]))

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    currencies, rub, _ = await seeded_currencies()
    wallets = InMemoryWalletRepository()
    client, workspace_id = make_client(wallets=wallets, currencies=currencies)
    wallet_id = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id])).json()["id"]
    url = wallets_url(workspace_id, f"/{wallet_id}")

    assert client.put(url, json=wallet_payload([rub.id], name=" ")).status_code == 400
    assert client.put(url, json=wallet_payload([rub.id], icon="nope")).status_code == 400
    assert client.put(url, json=wallet_payload([])).status_code == 400
    assert client.put(url, json=wallet_payload([rub.id, rub.id])).status_code == 400
    unknown_id = uuid4()
    assert client.put(url, json=wallet_payload([unknown_id])).status_code == 400


async def test_delete_unknown_wallet_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.delete(wallets_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


class RestrictingWalletRepository(InMemoryWalletRepository):
    """Симулирует `ON DELETE RESTRICT` `transactions.wallet_id`/`transfers.from_wallet_id`/`to_wallet_id`
    (реальный `WalletRepository` перехватывает `IntegrityError` и поднимает `ConflictError` — см. design.md
    `transactions`/`transfers`)."""

    def __init__(
        self,
        transactions: InMemoryTransactionRepository | None = None,
        transfers: InMemoryTransferRepository | None = None,
    ) -> None:
        super().__init__()
        self._transaction_repo = transactions
        self._transfer_repo = transfers

    async def delete(self, wallet_id: UUID, workspace_id: UUID) -> bool:
        if self._transaction_repo is not None and await self._transaction_repo.references_wallet(wallet_id):
            raise ConflictError("Кошелёк нельзя удалить: есть операции")
        if self._transfer_repo is not None and await self._transfer_repo.references_wallet(wallet_id):
            raise ConflictError("Кошелёк нельзя удалить: есть переводы")
        return await super().delete(wallet_id, workspace_id)


async def test_delete_wallet_with_transactions_returns_409() -> None:
    currencies, rub, _ = await seeded_currencies()
    categories = InMemoryCategoryRepository()
    transactions = InMemoryTransactionRepository(categories)
    wallets = RestrictingWalletRepository(transactions=transactions)
    client, workspace_id = make_client(
        wallets=wallets, currencies=currencies, categories=categories, transactions=transactions
    )
    wallet_id = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id])).json()["id"]
    category = await categories.add(
        Category(
            id=uuid4(),
            workspace_id=workspace_id,
            type=CategoryType.INCOME,
            name="Зарплата",
            icon="wallet",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    transaction = await transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=UUID(wallet_id),
            category_id=category.id,
            legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("10")),),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    response = client.delete(wallets_url(workspace_id, f"/{wallet_id}"))

    assert response.status_code == 409
    assert client.get(wallets_url(workspace_id, f"/{wallet_id}")).status_code == 200
    assert await transactions.get_by_id(transaction.id, workspace_id) is not None


async def test_delete_wallet_with_transfer_returns_409() -> None:
    currencies, rub, _ = await seeded_currencies()
    transfers = InMemoryTransferRepository()
    wallets = RestrictingWalletRepository(transfers=transfers)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, transfers=transfers)
    wallet_id = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id])).json()["id"]
    other_wallet_id = client.post(wallets_url(workspace_id), json=wallet_payload([rub.id], name="Второй")).json()["id"]
    transfer = await transfers.add(
        Transfer(
            id=uuid4(),
            workspace_id=workspace_id,
            from_wallet_id=UUID(wallet_id),
            to_wallet_id=UUID(other_wallet_id),
            currency_id=rub.id,
            amount=Decimal("10"),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    response = client.delete(wallets_url(workspace_id, f"/{wallet_id}"))

    assert response.status_code == 409
    assert client.get(wallets_url(workspace_id, f"/{wallet_id}")).status_code == 200
    assert await transfers.get_by_id(transfer.id, workspace_id) is not None


class TestWorkspaceIsolation:
    async def test_foreign_wallet_is_not_readable(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        wallet_id = client_a.post(wallets_url(workspace_a), json=wallet_payload([rub.id])).json()["id"]

        response = client_b.get(wallets_url(workspace_b, f"/{wallet_id}"))

        assert response.status_code == 404

    async def test_foreign_wallet_is_not_updatable(self) -> None:
        currencies, rub, cny = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        wallet_id = client_a.post(wallets_url(workspace_a), json=wallet_payload([rub.id])).json()["id"]

        response = client_b.put(wallets_url(workspace_b, f"/{wallet_id}"), json=wallet_payload([cny.id], name="Чужое"))

        assert response.status_code == 404
        assert client_a.get(wallets_url(workspace_a, f"/{wallet_id}")).json()["name"] == "Наличные"

    async def test_foreign_wallet_is_not_deletable(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        wallet_id = client_a.post(wallets_url(workspace_a), json=wallet_payload([rub.id])).json()["id"]

        response = client_b.delete(wallets_url(workspace_b, f"/{wallet_id}"))

        assert response.status_code == 404
        assert client_a.get(wallets_url(workspace_a, f"/{wallet_id}")).status_code == 200

    async def test_list_does_not_contain_other_workspaces_wallets(self) -> None:
        currencies, rub, _ = await seeded_currencies()
        wallets = InMemoryWalletRepository()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_a.post(wallets_url(workspace_a), json=wallet_payload([rub.id], name="Кошелёк A"))

        response = client_b.get(wallets_url(workspace_b))

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_using_foreign_workspace_id_in_path_is_404(self) -> None:
        """Чужой workspace_id в пути отклоняется на уровне `require_workspace`, до обращения к кошелькам."""
        currencies, rub, _ = await seeded_currencies()
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(currencies=currencies, workspaces=workspaces)
        client_b, _ = make_client(currencies=currencies, workspaces=workspaces)

        response = client_b.get(wallets_url(workspace_a))

        assert response.status_code == 404
