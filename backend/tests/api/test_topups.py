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


class Environment:
    """Воркспейс с валютой CNY, кошельками в CNY и RUB, категориями дохода и расхода."""

    def __init__(self) -> None:
        self.wallets = InMemoryWalletRepository()
        self.categories = InMemoryCategoryRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.workspaces = InMemoryWorkspaceRepository()
        self.user_id = uuid4()
        self.workspace_id = uuid4()

    async def setup(self) -> None:
        self.cny = await self.currency("CNY")
        self.rub = await self.currency("RUB")
        self.workspaces.seed(
            Workspace(
                id=self.workspace_id,
                user_id=self.user_id,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                name="Т",
                currency_id=self.cny.id,
            )
        )
        self.cny_wallet = await self.wallet(self.workspace_id, self.cny)
        self.rub_wallet = await self.wallet(self.workspace_id, self.rub)
        self.income = await self.category(self.workspace_id, CategoryType.INCOME)
        self.expense = await self.category(self.workspace_id, CategoryType.EXPENSE)

    def client(self, *, authenticated: bool = True, user_id: UUID | None = None) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_wallet_repository] = lambda: self.wallets
        app.dependency_overrides[get_category_repository] = lambda: self.categories
        app.dependency_overrides[get_currency_repository] = lambda: self.currencies
        app.dependency_overrides[get_transaction_repository] = lambda: self.transactions
        app.dependency_overrides[get_workspace_repository] = lambda: self.workspaces
        if authenticated:
            current_user_id = user_id if user_id is not None else self.user_id
            app.dependency_overrides[get_current_user] = lambda: current_user_id
        return TestClient(app)

    async def currency(self, code: str, decimal_places: int = 2) -> Currency:
        currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
        await self.currencies.upsert_many([currency])
        return currency

    async def wallet(self, workspace_id: UUID, currency: Currency) -> Wallet:
        return await self.wallets.add(
            Wallet(
                id=uuid4(),
                workspace_id=workspace_id,
                name="Кошелёк",
                icon="wallet",
                currency_id=currency.id,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    async def category(self, workspace_id: UUID, type: CategoryType) -> Category:
        return await self.categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace_id,
                type=type,
                name=f"Категория {uuid4()}",
                icon="wallet",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    def url(self, suffix: str = "") -> str:
        return f"/api/workspaces/{self.workspace_id}/topups{suffix}"


def leg(currency: Currency, amount: str) -> dict:
    return {"currency_id": str(currency.id), "amount": amount}


def by_currency(legs: list[dict]) -> list[dict]:
    return sorted(legs, key=lambda item: item["currency_id"])


def payload(wallet: Wallet, category: Category, legs: list[dict], **extra: str) -> dict:
    return {"wallet_id": str(wallet.id), "category_id": str(category.id), "legs": legs, **extra}


async def make_env() -> Environment:
    env = Environment()
    await env.setup()
    return env


class TestCreate:
    async def test_single_leg_when_wallet_currency_equals_workspace_currency(self) -> None:
        env = await make_env()

        response = env.client().post(
            env.url(),
            json=payload(env.cny_wallet, env.income, [leg(env.cny, "100.00")], occurred_at="2026-03-01T12:00:00"),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["wallet_id"] == str(env.cny_wallet.id)
        assert body["category_id"] == str(env.income.id)
        assert body["legs"] == [leg(env.cny, "100.00")]
        assert body["occurred_at"] == "2026-03-01T12:00:00"
        assert body["comment"] is None
        assert body["updated_at"] is None

    async def test_two_legs_when_currencies_differ(self) -> None:
        env = await make_env()

        response = env.client().post(
            env.url(), json=payload(env.rub_wallet, env.income, [leg(env.rub, "10000.00"), leg(env.cny, "780.00")])
        )

        assert response.status_code == 201
        assert by_currency(response.json()["legs"]) == by_currency([leg(env.cny, "780.00"), leg(env.rub, "10000.00")])

    async def test_without_date_uses_server_time(self) -> None:
        env = await make_env()

        response = env.client().post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")]))

        assert response.status_code == 201
        assert response.json()["occurred_at"] is not None

    async def test_two_legs_for_same_currency_wallet_is_rejected(self) -> None:
        env = await make_env()

        response = env.client().post(
            env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1"), leg(env.rub, "2")])
        )

        assert response.status_code == 400
        assert "RUB" in response.json()["detail"]

    async def test_single_leg_for_other_currency_wallet_is_rejected(self) -> None:
        env = await make_env()

        for currency in (env.cny, env.rub):
            response = env.client().post(env.url(), json=payload(env.rub_wallet, env.income, [leg(currency, "1")]))

            assert response.status_code == 400

    async def test_third_currency_is_rejected(self) -> None:
        env = await make_env()
        usdt = await env.currency("USDT")

        response = env.client().post(
            env.url(), json=payload(env.rub_wallet, env.income, [leg(env.cny, "1"), leg(usdt, "1")])
        )

        assert response.status_code == 400

    async def test_duplicate_currency_is_rejected(self) -> None:
        env = await make_env()

        response = env.client().post(
            env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1"), leg(env.cny, "2")])
        )

        assert response.status_code == 400

    async def test_empty_legs_are_rejected(self) -> None:
        env = await make_env()

        response = env.client().post(env.url(), json=payload(env.cny_wallet, env.income, []))

        assert response.status_code == 400

    async def test_expense_category_is_rejected(self) -> None:
        env = await make_env()

        response = env.client().post(env.url(), json=payload(env.cny_wallet, env.expense, [leg(env.cny, "1")]))

        assert response.status_code == 400

    async def test_nonpositive_amount_is_rejected(self) -> None:
        env = await make_env()

        for amount in ("0", "-5"):
            response = env.client().post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, amount)]))

            assert response.status_code == 400

    async def test_amount_exceeding_decimal_places_is_rejected(self) -> None:
        env = await make_env()

        response = env.client().post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1.001")]))

        assert response.status_code == 400

    async def test_unknown_wallet_and_category_return_404(self) -> None:
        env = await make_env()
        client = env.client()

        unknown_wallet = {**payload(env.cny_wallet, env.income, [leg(env.cny, "1")]), "wallet_id": str(uuid4())}
        unknown_category = {**payload(env.cny_wallet, env.income, [leg(env.cny, "1")]), "category_id": str(uuid4())}

        assert client.post(env.url(), json=unknown_wallet).status_code == 404
        assert client.post(env.url(), json=unknown_category).status_code == 404

    async def test_foreign_workspace_returns_404(self) -> None:
        env = await make_env()

        response = env.client(user_id=uuid4()).post(
            env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])
        )

        assert response.status_code == 404

    async def test_without_session_is_401(self) -> None:
        env = await make_env()

        response = env.client(authenticated=False).post(
            env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])
        )

        assert response.status_code == 401

    async def test_comment_is_saved_normalized_and_limited(self) -> None:
        env = await make_env()
        client = env.client()
        base = payload(env.cny_wallet, env.income, [leg(env.cny, "1")])

        saved = client.post(env.url(), json={**base, "comment": "Обмен в банке"})
        blank = client.post(env.url(), json={**base, "comment": "   "})
        too_long = client.post(env.url(), json={**base, "comment": "я" * 1001})

        assert saved.json()["comment"] == "Обмен в банке"
        assert blank.json()["comment"] is None
        assert too_long.status_code == 400


class TestReadAndList:
    async def test_get_returns_topup_with_legs(self) -> None:
        env = await make_env()
        client = env.client()
        topup_id = client.post(
            env.url(), json=payload(env.rub_wallet, env.income, [leg(env.cny, "780"), leg(env.rub, "10000")])
        ).json()["id"]

        response = client.get(env.url(f"/{topup_id}"))

        assert response.status_code == 200
        assert response.json()["id"] == topup_id
        assert len(response.json()["legs"]) == 2

    async def test_get_unknown_returns_404(self) -> None:
        env = await make_env()

        assert env.client().get(env.url(f"/{uuid4()}")).status_code == 404

    async def test_list_contains_only_topups_sorted_and_filtered(self) -> None:
        env = await make_env()
        client = env.client()
        old_id = client.post(
            env.url(),
            json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")], occurred_at="2026-01-01T00:00:00"),
        ).json()["id"]
        new_id = client.post(
            env.url(),
            json=payload(
                env.rub_wallet, env.income, [leg(env.cny, "7"), leg(env.rub, "90")], occurred_at="2026-02-01T00:00:00"
            ),
        ).json()["id"]
        client.post(
            f"/api/workspaces/{env.workspace_id}/transactions",
            json={
                "wallet_id": str(env.cny_wallet.id),
                "category_id": str(env.expense.id),
                "currency_id": str(env.cny.id),
                "amount": "5",
            },
        )

        everything = client.get(env.url()).json()
        by_wallet = client.get(env.url(), params={"wallet_id": str(env.rub_wallet.id)}).json()
        by_date = client.get(env.url(), params={"date_to": "2026-01-15T00:00:00"}).json()

        assert [item["id"] for item in everything["items"]] == [new_id, old_id]
        assert everything["total"] == 2
        assert [item["id"] for item in by_wallet["items"]] == [new_id]
        assert [item["id"] for item in by_date["items"]] == [old_id]

    async def test_list_validates_dates_and_pagination(self) -> None:
        env = await make_env()
        client = env.client()

        inverted = client.get(env.url(), params={"date_from": "2026-02-01T00:00:00", "date_to": "2026-01-01T00:00:00"})
        bad_limit = client.get(env.url(), params={"limit": 0})
        default = client.get(env.url()).json()

        assert inverted.status_code == 400
        assert bad_limit.status_code == 400
        assert (default["limit"], default["offset"]) == (20, 0)

    async def test_expense_is_not_readable_as_topup(self) -> None:
        env = await make_env()
        client = env.client()
        expense_id = client.post(
            f"/api/workspaces/{env.workspace_id}/transactions",
            json={
                "wallet_id": str(env.cny_wallet.id),
                "category_id": str(env.expense.id),
                "amount": "5",
            },
        ).json()["id"]

        assert client.get(env.url(f"/{expense_id}")).status_code == 404
        assert client.get(env.url()).json()["total"] == 0


class TestUpdate:
    async def test_put_replaces_everything(self) -> None:
        env = await make_env()
        client = env.client()
        topup_id = client.post(
            env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")], comment="Старый")
        ).json()["id"]

        response = client.put(
            env.url(f"/{topup_id}"),
            json=payload(env.rub_wallet, env.income, [leg(env.cny, "780"), leg(env.rub, "10000")]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["wallet_id"] == str(env.rub_wallet.id)
        assert by_currency(body["legs"]) == by_currency([leg(env.cny, "780"), leg(env.rub, "10000")])
        assert body["comment"] is None
        assert body["updated_at"] is not None

    async def test_put_validates_like_create(self) -> None:
        env = await make_env()
        client = env.client()
        topup_id = client.post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])).json()["id"]

        wrong_legs = client.put(env.url(f"/{topup_id}"), json=payload(env.rub_wallet, env.income, [leg(env.cny, "1")]))
        expense = client.put(env.url(f"/{topup_id}"), json=payload(env.cny_wallet, env.expense, [leg(env.cny, "1")]))

        assert wrong_legs.status_code == 400
        assert expense.status_code == 400
        assert client.get(env.url(f"/{topup_id}")).json()["legs"] == [leg(env.cny, "1")]

    async def test_put_unknown_returns_404(self) -> None:
        env = await make_env()

        response = env.client().put(
            env.url(f"/{uuid4()}"), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])
        )

        assert response.status_code == 404


class TestDelete:
    async def test_delete_removes_topup(self) -> None:
        env = await make_env()
        client = env.client()
        topup_id = client.post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])).json()["id"]

        response = client.delete(env.url(f"/{topup_id}"))

        assert response.status_code == 204
        assert client.get(env.url(f"/{topup_id}")).status_code == 404

    async def test_delete_unknown_returns_404(self) -> None:
        env = await make_env()

        assert env.client().delete(env.url(f"/{uuid4()}")).status_code == 404


class TestWorkspaceIsolation:
    async def test_foreign_user_cannot_read_update_or_delete(self) -> None:
        env = await make_env()
        topup_id = (
            env.client().post(env.url(), json=payload(env.cny_wallet, env.income, [leg(env.cny, "1")])).json()["id"]
        )
        stranger = env.client(user_id=uuid4())

        assert stranger.get(env.url(f"/{topup_id}")).status_code == 404
        assert stranger.get(env.url()).status_code == 404
        updated = stranger.put(env.url(f"/{topup_id}"), json=payload(env.cny_wallet, env.income, [leg(env.cny, "2")]))
        assert updated.status_code == 404
        assert stranger.delete(env.url(f"/{topup_id}")).status_code == 404
        assert env.client().get(env.url(f"/{topup_id}")).status_code == 200

    async def test_topup_of_another_workspace_is_not_visible_through_own_workspace(self) -> None:
        env = await make_env()
        other_workspace_id = uuid4()
        env.workspaces.seed(
            Workspace(
                id=other_workspace_id,
                user_id=env.user_id,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                name="Другой",
                currency_id=env.cny.id,
            )
        )
        other_wallet = await env.wallet(other_workspace_id, env.cny)
        other_income = await env.category(other_workspace_id, CategoryType.INCOME)
        client = env.client()
        other_id = client.post(
            f"/api/workspaces/{other_workspace_id}/topups",
            json=payload(other_wallet, other_income, [leg(env.cny, "1")]),
        ).json()["id"]

        assert client.get(env.url(f"/{other_id}")).status_code == 404
        assert client.get(env.url()).json()["total"] == 0
        cross_wallet = client.post(env.url(), json=payload(other_wallet, env.income, [leg(env.cny, "1")]))
        assert cross_wallet.status_code == 404
