from uuid import uuid4

from fastapi.testclient import TestClient

from core.entities import Currency
from depends.currency import get_currency_repository
from main import create_app
from tests.fakes import InMemoryCurrencyRepository


def make_client(repo: InMemoryCurrencyRepository | None = None) -> TestClient:
    app = create_app()
    repo = repo if repo is not None else InMemoryCurrencyRepository()
    app.dependency_overrides[get_currency_repository] = lambda: repo
    return TestClient(app)


async def seeded_repo() -> InMemoryCurrencyRepository:
    repo = InMemoryCurrencyRepository()
    await repo.upsert_many(
        [
            Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2),
            Currency(id=uuid4(), code="CNY", name="Китайский юань", decimal_places=2),
            Currency(id=uuid4(), code="USDT", name="USDT", decimal_places=2),
        ]
    )
    return repo


async def test_list_default_pagination() -> None:
    client = make_client(await seeded_repo())

    response = client.get("/api/currencies")

    assert response.status_code == 200
    body = response.json()
    assert [item["code"] for item in body["items"]] == ["CNY", "RUB", "USDT"]
    assert (body["total"], body["limit"], body["offset"]) == (3, 20, 0)


async def test_list_item_fields() -> None:
    client = make_client(await seeded_repo())

    response = client.get("/api/currencies")

    item = response.json()["items"][0]
    assert set(item.keys()) == {"id", "code", "name", "decimal_places"}


async def test_list_applies_explicit_pagination() -> None:
    client = make_client(await seeded_repo())

    response = client.get("/api/currencies", params={"limit": 1, "offset": 1})

    body = response.json()
    assert [item["code"] for item in body["items"]] == ["RUB"]
    assert body["total"] == 3


async def test_list_invalid_limit_returns_400() -> None:
    client = make_client()

    response = client.get("/api/currencies", params={"limit": 0})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], list)


async def test_list_invalid_offset_returns_400() -> None:
    client = make_client()

    response = client.get("/api/currencies", params={"offset": -1})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], list)
