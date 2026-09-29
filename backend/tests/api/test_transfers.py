from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Currency, Wallet
from depends.auth import get_current_user
from depends.currency import get_currency_repository
from depends.transfer import get_transfer_repository
from depends.wallet import get_wallet_repository
from main import create_app
from tests.fakes import InMemoryCurrencyRepository, InMemoryTransferRepository, InMemoryWalletRepository


def make_client(
    *,
    wallets: InMemoryWalletRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transfers: InMemoryTransferRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    wallets = wallets if wallets is not None else InMemoryWalletRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transfers = transfers if transfers is not None else InMemoryTransferRepository()
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_wallet_repository] = lambda: wallets
    app.dependency_overrides[get_currency_repository] = lambda: currencies
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


def transfer_payload(
    *,
    from_wallet_id: UUID,
    to_wallet_id: UUID,
    currency_id: UUID,
    amount: str = "10.00",
    occurred_at: str | None = None,
) -> dict:
    payload = {
        "from_wallet_id": str(from_wallet_id),
        "to_wallet_id": str(to_wallet_id),
        "currency_id": str(currency_id),
        "amount": amount,
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return payload


async def make_environment(
    user_id: UUID,
) -> tuple[InMemoryWalletRepository, InMemoryCurrencyRepository, Wallet, Wallet, Currency]:
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    currency = await make_currency(currencies)
    from_wallet = await make_wallet(wallets, user_id, [currency.id])
    to_wallet = await make_wallet(wallets, user_id, [currency.id])
    return wallets, currencies, from_wallet, to_wallet, currency


async def test_create_transfer_with_explicit_date() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            currency_id=currency.id,
            occurred_at="2026-03-01T12:00:00Z",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["from_wallet_id"] == str(from_wallet.id)
    assert body["to_wallet_id"] == str(to_wallet.id)
    assert body["currency_id"] == str(currency.id)
    assert body["amount"] == "10.00"
    assert body["occurred_at"] == "2026-03-01T12:00:00Z"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_transfer_without_date_uses_server_time() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
    )

    assert response.status_code == 201
    assert response.json()["occurred_at"] is not None


async def test_create_transfer_rejects_no_shared_currency() -> None:
    user_id = uuid4()
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    from_wallet = await make_wallet(wallets, user_id, [rub.id])
    to_wallet = await make_wallet(wallets, user_id, [cny.id])
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=rub.id),
    )

    assert response.status_code == 400


async def test_create_transfer_rejects_same_wallet() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, _, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=from_wallet.id, currency_id=currency.id),
    )

    assert response.status_code == 400


async def test_create_transfer_rejects_unknown_from_wallet() -> None:
    user_id = uuid4()
    wallets, currencies, _, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=uuid4(), to_wallet_id=to_wallet.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transfer_rejects_foreign_to_wallet() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(uuid4())
    wallets2 = InMemoryWalletRepository()
    own_from_wallet = await make_wallet(wallets2, user_id, [currency.id])
    client = make_client(wallets=wallets2, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=own_from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_create_transfer_rejects_nonpositive_amount() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(
            from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id, amount="0"
        ),
    )

    assert response.status_code == 400


async def test_create_transfer_rejects_amount_exceeding_decimal_places() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.post(
        "/api/transfers",
        json=transfer_payload(
            from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id, amount="1.005"
        ),
    )

    assert response.status_code == 400


async def test_create_transfer_without_session_is_401() -> None:
    client = make_client(authenticated=False)

    response = client.post(
        "/api/transfers", json=transfer_payload(from_wallet_id=uuid4(), to_wallet_id=uuid4(), currency_id=uuid4())
    )

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    other_wallet = await make_wallet(wallets, user_id, [currency.id])
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    created = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
    ).json()
    transfer_id = created["id"]

    got = client.get(f"/api/transfers/{transfer_id}")
    assert got.status_code == 200
    assert got.json()["id"] == transfer_id

    listed = client.get("/api/transfers")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == transfer_id

    updated = client.put(
        f"/api/transfers/{transfer_id}",
        json=transfer_payload(
            from_wallet_id=to_wallet.id, to_wallet_id=other_wallet.id, currency_id=currency.id, amount="55.00"
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["from_wallet_id"] == str(to_wallet.id)
    assert updated.json()["to_wallet_id"] == str(other_wallet.id)
    assert updated.json()["amount"] == "55.00"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(f"/api/transfers/{transfer_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/transfers/{transfer_id}")
    assert after_delete.status_code == 404


async def test_get_unknown_transfer_returns_404() -> None:
    client = make_client()

    response = client.get(f"/api/transfers/{uuid4()}")

    assert response.status_code == 404


async def test_put_unknown_transfer_returns_404() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)

    response = client.put(
        f"/api/transfers/{uuid4()}",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
    )

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    user_id = uuid4()
    wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
    client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)
    transfer_id = client.post(
        "/api/transfers",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
    ).json()["id"]

    same_wallet_response = client.put(
        f"/api/transfers/{transfer_id}",
        json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=from_wallet.id, currency_id=currency.id),
    )
    assert same_wallet_response.status_code == 400

    amount_response = client.put(
        f"/api/transfers/{transfer_id}",
        json=transfer_payload(
            from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id, amount="0"
        ),
    )
    assert amount_response.status_code == 400


async def test_delete_unknown_transfer_returns_404() -> None:
    client = make_client()

    response = client.delete(f"/api/transfers/{uuid4()}")

    assert response.status_code == 404


class TestFiltersAndSorting:
    async def test_filter_by_wallet_matches_from_or_to(self) -> None:
        user_id = uuid4()
        wallets, currencies, wallet_a, wallet_b, currency = await make_environment(user_id)
        wallet_c = await make_wallet(wallets, user_id, [currency.id])
        client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=wallet_a.id, to_wallet_id=wallet_b.id, currency_id=currency.id),
        )
        client.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=wallet_b.id, to_wallet_id=wallet_c.id, currency_id=currency.id),
        )
        client.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=wallet_c.id, to_wallet_id=wallet_a.id, currency_id=currency.id),
        )

        response = client.get("/api/transfers", params={"wallet_id": str(wallet_b.id)})

        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_filter_by_date_range(self) -> None:
        user_id = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
        client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)
        client.post(
            "/api/transfers",
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        )
        client.post(
            "/api/transfers",
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        )

        response = client.get(
            "/api/transfers", params={"date_from": "2025-12-01T00:00:00Z", "date_to": "2026-02-01T00:00:00Z"}
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_invalid_date_range_returns_400(self) -> None:
        client = make_client()

        response = client.get(
            "/api/transfers", params={"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"}
        )

        assert response.status_code == 400

    async def test_list_sorted_by_occurred_at_desc(self) -> None:
        user_id = uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_id)
        client = make_client(wallets=wallets, currencies=currencies, user_id=user_id)
        early = client.post(
            "/api/transfers",
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                currency_id=currency.id,
                occurred_at="2026-01-01T00:00:00Z",
            ),
        ).json()
        late = client.post(
            "/api/transfers",
            json=transfer_payload(
                from_wallet_id=from_wallet.id,
                to_wallet_id=to_wallet.id,
                currency_id=currency.id,
                occurred_at="2026-06-01T00:00:00Z",
            ),
        ).json()

        response = client.get("/api/transfers")

        ids = [item["id"] for item in response.json()["items"]]
        assert ids == [late["id"], early["id"]]

    async def test_default_pagination(self) -> None:
        client = make_client()

        response = client.get("/api/transfers")

        assert response.status_code == 200
        assert response.json()["limit"] == 20
        assert response.json()["offset"] == 0

    async def test_invalid_pagination_params_rejected(self) -> None:
        client = make_client()

        assert client.get("/api/transfers", params={"limit": 0}).status_code == 400
        assert client.get("/api/transfers", params={"limit": 101}).status_code == 400
        assert client.get("/api/transfers", params={"offset": -1}).status_code == 400


class TestUserIsolation:
    async def test_foreign_transfer_is_not_readable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        transfer_id = client_a.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.get(f"/api/transfers/{transfer_id}")

        assert response.status_code == 404

    async def test_foreign_transfer_is_not_updatable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        transfer_id = client_a.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.put(
            f"/api/transfers/{transfer_id}",
            json=transfer_payload(
                from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id, amount="1.00"
            ),
        )

        assert response.status_code == 404
        assert client_a.get(f"/api/transfers/{transfer_id}").json()["amount"] == "10.00"

    async def test_foreign_transfer_is_not_deletable(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        transfer_id = client_a.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
        ).json()["id"]

        response = client_b.delete(f"/api/transfers/{transfer_id}")

        assert response.status_code == 404
        assert client_a.get(f"/api/transfers/{transfer_id}").status_code == 200

    async def test_list_does_not_contain_other_users_transfers(self) -> None:
        user_a, user_b = uuid4(), uuid4()
        wallets, currencies, from_wallet, to_wallet, currency = await make_environment(user_a)
        client_a = make_client(wallets=wallets, currencies=currencies, user_id=user_a)
        client_b = make_client(wallets=wallets, currencies=currencies, user_id=user_b)
        client_a.post(
            "/api/transfers",
            json=transfer_payload(from_wallet_id=from_wallet.id, to_wallet_id=to_wallet.id, currency_id=currency.id),
        )

        response = client_b.get("/api/transfers")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0
