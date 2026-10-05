from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Currency, Wallet, Workspace
from depends.auth import get_current_user
from depends.currency import get_currency_repository
from depends.transfer import get_transfer_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository
from main import create_app
from tests.fakes import (
    InMemoryCurrencyRepository,
    InMemoryTransferRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transfers: InMemoryTransferRepository | None = None,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transfers = transfers if transfers is not None else InMemoryTransferRepository()
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
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transfer_repository] = lambda: transfers
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), workspace_id


def transfers_url(workspace_id: UUID, suffix: str = "") -> str:
    return f"/api/workspaces/{workspace_id}/transfers{suffix}"


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


def transfer_payload(
    *,
    from_wallet_id: UUID,
    to_wallet_id: UUID,
    amount: str = "10.00",
    occurred_at: str | None = None,
) -> dict:
    payload = {
        "from_wallet_id": str(from_wallet_id),
        "to_wallet_id": str(to_wallet_id),
        "amount": amount,
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return payload


async def make_environment(
    workspace_id: UUID,
) -> tuple[InMemoryWalletRepository, InMemoryCurrencyRepository, Wallet, Wallet, Currency]:
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, workspace_id, currency.id)
    to_wallet = await make_wallet(wallets, workspace_id, currency.id)
    return wallets, currencies, from_wallet, to_wallet, currency


async def test_create_transfer_with_explicit_date() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            occurred_at="2026-03-01T12:00:00Z",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["from_wallet_id"] == str(from_wallet.id)
    assert body["to_wallet_id"] == str(to_wallet.id)
    assert body["amount"] == "10.00"
    assert body["occurred_at"] == "2026-03-01T12:00:00Z"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_transfer_without_date_uses_server_time() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
    )

    assert response.status_code == 201
    assert response.json()["occurred_at"] is not None


async def test_create_transfer_rejects_different_wallet_currencies() -> None:
    workspace_id = uuid4()
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    from_wallet = await make_wallet(wallets, workspace_id, rub.id)
    to_wallet = await make_wallet(wallets, workspace_id, cny.id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
    )

    assert response.status_code == 400
    assert "одной валюты" in response.json()["detail"]


async def test_create_transfer_rejects_currency_id_in_request() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json={
            **transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
            "currency_id": str(currency.id),
        },
    )

    assert response.status_code == 400
    assert client.get(transfers_url(workspace_id)).json()["total"] == 0


async def test_create_transfer_response_has_no_currency_id() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, _ = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    created = client.post(
        transfers_url(workspace_id), json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id)
    ).json()

    assert "currency_id" not in created
    assert "currency_id" not in client.get(transfers_url(workspace_id, f"/{created['id']}")).json()


async def test_create_transfer_rejects_same_wallet() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, _, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=from_wallet.id),
    )

    assert response.status_code == 400


async def test_create_transfer_rejects_unknown_from_wallet() -> None:
    workspace_id = uuid4()
    wallets, currencies, _, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=uuid4(), to_wallet_id=to_wallet.id),
    )

    assert response.status_code == 404


async def test_create_transfer_rejects_foreign_to_wallet() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(uuid4())
    wallets2 = InMemoryWalletRepository()
    own_from_wallet = await make_wallet(wallets2, workspace_id, currency.id)
    client, workspace_id = make_client(wallets=wallets2, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=own_from_wallet.id, to_wallet_id=to_wallet.id),
    )

    assert response.status_code == 404


async def test_create_transfer_rejects_nonpositive_amount() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, amount="0"),
    )

    assert response.status_code == 400


async def test_create_transfer_rejects_amount_exceeding_decimal_places() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, amount="1.005"),
    )

    assert response.status_code == 400


async def test_create_transfer_without_session_is_401() -> None:
    client, workspace_id = make_client(authenticated=False)

    response = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=uuid4(), to_wallet_id=uuid4()),
    )

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    other_wallet = await make_wallet(wallets, workspace_id, currency.id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    created = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
    ).json()
    transfer_id = created["id"]

    got = client.get(transfers_url(workspace_id, f"/{transfer_id}"))
    assert got.status_code == 200
    assert got.json()["id"] == transfer_id

    listed = client.get(transfers_url(workspace_id))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == transfer_id

    updated = client.put(
        transfers_url(workspace_id, f"/{transfer_id}"),
        json=transfer_payload(from_wallet_id=to_wallet.id, to_wallet_id=other_wallet.id, amount="55.00"),
    )
    assert updated.status_code == 200
    assert updated.json()["from_wallet_id"] == str(to_wallet.id)
    assert updated.json()["to_wallet_id"] == str(other_wallet.id)
    assert updated.json()["amount"] == "55.00"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(transfers_url(workspace_id, f"/{transfer_id}"))
    assert deleted.status_code == 204

    after_delete = client.get(transfers_url(workspace_id, f"/{transfer_id}"))
    assert after_delete.status_code == 404


async def test_get_unknown_transfer_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.get(transfers_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


async def test_put_unknown_transfer_returns_404() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)

    response = client.put(
        transfers_url(workspace_id, f"/{uuid4()}"),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
    )

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    workspace_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
    client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)
    transfer_id = client.post(
        transfers_url(workspace_id),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
    ).json()["id"]

    same_wallet_response = client.put(
        transfers_url(workspace_id, f"/{transfer_id}"),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=from_wallet.id),
    )
    assert same_wallet_response.status_code == 400

    amount_response = client.put(
        transfers_url(workspace_id, f"/{transfer_id}"),
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, amount="0"),
    )
    assert amount_response.status_code == 400


async def test_delete_unknown_transfer_returns_404() -> None:
    client, workspace_id = make_client()

    response = client.delete(transfers_url(workspace_id, f"/{uuid4()}"))

    assert response.status_code == 404


class TestFiltersAndSorting:
    async def test_filter_by_wallet_matches_from_or_to(self) -> None:
        workspace_id = uuid4()
        wallets, currencies, wallet_a, wallet_b, currency = await make_environment(workspace_id)
        wallet_c = await make_wallet(wallets, workspace_id, currency.id)
        client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)
        client.post(
            transfers_url(workspace_id),
            json=transfer_payload(from_wallet_id=wallet_a.id, to_wallet_id=wallet_b.id),
        )
        client.post(
            transfers_url(workspace_id),
            json=transfer_payload(from_wallet_id=wallet_b.id, to_wallet_id=wallet_c.id),
        )
        client.post(
            transfers_url(workspace_id),
            json=transfer_payload(from_wallet_id=wallet_c.id, to_wallet_id=wallet_a.id),
        )

        response = client.get(transfers_url(workspace_id), params={"wallet_id": str(wallet_b.id)})

        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_filter_by_date_range(self) -> None:
        workspace_id = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)
        client.post(
            transfers_url(workspace_id),
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        )
        client.post(
            transfers_url(workspace_id),
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        )

        response = client.get(
            transfers_url(workspace_id),
            params={"date_from": "2025-12-01T00:00:00Z", "date_to": "2026-02-01T00:00:00Z"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_invalid_date_range_returns_400(self) -> None:
        client, workspace_id = make_client()

        response = client.get(
            transfers_url(workspace_id),
            params={"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
        )

        assert response.status_code == 400

    async def test_list_sorted_by_occurred_at_desc(self) -> None:
        workspace_id = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_id)
        client, workspace_id = make_client(wallets=wallets, currencies=currencies, workspace_id=workspace_id)
        early = client.post(
            transfers_url(workspace_id),
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        ).json()
        late = client.post(
            transfers_url(workspace_id),
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        ).json()

        response = client.get(transfers_url(workspace_id))

        ids = [item["id"] for item in response.json()["items"]]
        assert ids == [late["id"], early["id"]]

    async def test_default_pagination(self) -> None:
        client, workspace_id = make_client()

        response = client.get(transfers_url(workspace_id))

        assert response.status_code == 200
        assert response.json()["limit"] == 20
        assert response.json()["offset"] == 0

    async def test_invalid_pagination_params_rejected(self) -> None:
        client, workspace_id = make_client()

        assert client.get(transfers_url(workspace_id), params={"limit": 0}).status_code == 400
        assert client.get(transfers_url(workspace_id), params={"limit": 101}).status_code == 400
        assert client.get(transfers_url(workspace_id), params={"offset": -1}).status_code == 400


class TestWorkspaceIsolation:
    async def test_foreign_transfer_is_not_readable(self) -> None:
        workspace_a = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets, currencies=currencies, workspaces=workspaces, workspace_id=workspace_a
        )
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        transfer_id = client_a.post(
            transfers_url(workspace_a),
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
        ).json()["id"]

        response = client_b.get(transfers_url(workspace_b, f"/{transfer_id}"))

        assert response.status_code == 404

    async def test_foreign_transfer_is_not_updatable(self) -> None:
        workspace_a = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets, currencies=currencies, workspaces=workspaces, workspace_id=workspace_a
        )
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        transfer_id = client_a.post(
            transfers_url(workspace_a),
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
        ).json()["id"]

        response = client_b.put(
            transfers_url(workspace_b, f"/{transfer_id}"),
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, amount="1.00"),
        )

        assert response.status_code == 404
        assert client_a.get(transfers_url(workspace_a, f"/{transfer_id}")).json()["amount"] == "10.00"

    async def test_foreign_transfer_is_not_deletable(self) -> None:
        workspace_a = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets, currencies=currencies, workspaces=workspaces, workspace_id=workspace_a
        )
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        transfer_id = client_a.post(
            transfers_url(workspace_a),
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
        ).json()["id"]

        response = client_b.delete(transfers_url(workspace_b, f"/{transfer_id}"))

        assert response.status_code == 404
        assert client_a.get(transfers_url(workspace_a, f"/{transfer_id}")).status_code == 200

    async def test_list_does_not_contain_other_workspaces_transfers(self) -> None:
        workspace_a = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(workspace_a)
        workspaces = InMemoryWorkspaceRepository()
        client_a, workspace_a = make_client(
            wallets=wallets, currencies=currencies, workspaces=workspaces, workspace_id=workspace_a
        )
        client_b, workspace_b = make_client(wallets=wallets, currencies=currencies, workspaces=workspaces)
        client_a.post(
            transfers_url(workspace_a),
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id),
        )

        response = client_b.get(transfers_url(workspace_b))

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0
