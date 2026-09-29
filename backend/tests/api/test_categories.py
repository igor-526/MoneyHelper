from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from depends.auth import get_current_user
from depends.category import get_category_repository
from main import create_app
from tests.fakes import InMemoryCategoryRepository


def make_client(
    *,
    categories: InMemoryCategoryRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    categories = categories if categories is not None else InMemoryCategoryRepository()
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_category_repository] = lambda: categories
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app)


def category_payload(type: str = "income", name: str = "Зарплата", icon: str = "wallet") -> dict:
    return {"type": type, "name": name, "icon": icon}


async def test_create_income_category() -> None:
    client = make_client()

    response = client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "income"
    assert body["name"] == "Зарплата"
    assert body["icon"] == "wallet"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_expense_category() -> None:
    client = make_client()

    response = client.post("/api/categories", json=category_payload(type="expense", name="Продукты"))

    assert response.status_code == 201
    assert response.json()["type"] == "expense"


async def test_create_category_rejects_empty_name() -> None:
    client = make_client()

    response = client.post("/api/categories", json=category_payload(name="   "))

    assert response.status_code == 400


async def test_create_category_rejects_unknown_icon() -> None:
    client = make_client()

    response = client.post("/api/categories", json=category_payload(icon="not-an-icon"))

    assert response.status_code == 400


async def test_create_category_rejects_invalid_type() -> None:
    client = make_client()

    response = client.post("/api/categories", json=category_payload(type="savings"))

    assert response.status_code == 400


async def test_create_category_duplicate_name_within_type_is_409() -> None:
    categories = InMemoryCategoryRepository()
    client = make_client(categories=categories)
    client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))

    response = client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))

    assert response.status_code == 409


async def test_create_category_same_name_different_type_is_allowed() -> None:
    categories = InMemoryCategoryRepository()
    client = make_client(categories=categories)
    client.post("/api/categories", json=category_payload(type="income", name="Прочее"))

    response = client.post("/api/categories", json=category_payload(type="expense", name="Прочее"))

    assert response.status_code == 201


async def test_create_category_without_session_is_401() -> None:
    client = make_client(authenticated=False)

    response = client.post("/api/categories", json=category_payload())

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    categories = InMemoryCategoryRepository()
    client = make_client(categories=categories)

    created = client.post("/api/categories", json=category_payload(type="income", name="Зарплата")).json()
    category_id = created["id"]

    got = client.get(f"/api/categories/{category_id}")
    assert got.status_code == 200
    assert got.json()["id"] == category_id

    listed = client.get("/api/categories")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == category_id

    updated = client.put(f"/api/categories/{category_id}", json=category_payload(type="expense", name="Обновлённая"))
    assert updated.status_code == 200
    assert updated.json()["type"] == "expense"
    assert updated.json()["name"] == "Обновлённая"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(f"/api/categories/{category_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/categories/{category_id}")
    assert after_delete.status_code == 404


async def test_get_unknown_category_returns_404() -> None:
    client = make_client()

    response = client.get(f"/api/categories/{uuid4()}")

    assert response.status_code == 404


async def test_put_unknown_category_returns_404() -> None:
    client = make_client()

    response = client.put(f"/api/categories/{uuid4()}", json=category_payload())

    assert response.status_code == 404


async def test_put_validates_input_like_create() -> None:
    categories = InMemoryCategoryRepository()
    client = make_client(categories=categories)
    category_id = client.post("/api/categories", json=category_payload()).json()["id"]

    assert client.put(f"/api/categories/{category_id}", json=category_payload(name=" ")).status_code == 400
    assert client.put(f"/api/categories/{category_id}", json=category_payload(icon="nope")).status_code == 400
    assert client.put(f"/api/categories/{category_id}", json=category_payload(type="nope")).status_code == 400


async def test_put_duplicate_name_conflict() -> None:
    categories = InMemoryCategoryRepository()
    client = make_client(categories=categories)
    client.post("/api/categories", json=category_payload(type="income", name="A"))
    category_b_id = client.post("/api/categories", json=category_payload(type="income", name="B")).json()["id"]

    response = client.put(f"/api/categories/{category_b_id}", json=category_payload(type="income", name="A"))

    assert response.status_code == 409


async def test_delete_unknown_category_returns_404() -> None:
    client = make_client()

    response = client.delete(f"/api/categories/{uuid4()}")

    assert response.status_code == 404


class TestTypeFilter:
    async def test_filter_by_income(self) -> None:
        categories = InMemoryCategoryRepository()
        client = make_client(categories=categories)
        client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))
        client.post("/api/categories", json=category_payload(type="expense", name="Продукты"))

        response = client.get("/api/categories", params={"type": "income"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "income"

    async def test_filter_by_expense(self) -> None:
        categories = InMemoryCategoryRepository()
        client = make_client(categories=categories)
        client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))
        client.post("/api/categories", json=category_payload(type="expense", name="Продукты"))

        response = client.get("/api/categories", params={"type": "expense"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "expense"

    async def test_without_filter_returns_both_types(self) -> None:
        categories = InMemoryCategoryRepository()
        client = make_client(categories=categories)
        client.post("/api/categories", json=category_payload(type="income", name="Зарплата"))
        client.post("/api/categories", json=category_payload(type="expense", name="Продукты"))

        response = client.get("/api/categories")

        assert response.status_code == 200
        assert response.json()["total"] == 2


class TestUserIsolation:
    async def test_foreign_category_is_not_readable(self) -> None:
        categories = InMemoryCategoryRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(categories=categories, user_id=user_a)
        client_b = make_client(categories=categories, user_id=user_b)
        category_id = client_a.post("/api/categories", json=category_payload()).json()["id"]

        response = client_b.get(f"/api/categories/{category_id}")

        assert response.status_code == 404

    async def test_foreign_category_is_not_updatable(self) -> None:
        categories = InMemoryCategoryRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(categories=categories, user_id=user_a)
        client_b = make_client(categories=categories, user_id=user_b)
        category_id = client_a.post("/api/categories", json=category_payload(name="Зарплата")).json()["id"]

        response = client_b.put(f"/api/categories/{category_id}", json=category_payload(name="Чужое"))

        assert response.status_code == 404
        assert client_a.get(f"/api/categories/{category_id}").json()["name"] == "Зарплата"

    async def test_foreign_category_is_not_deletable(self) -> None:
        categories = InMemoryCategoryRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(categories=categories, user_id=user_a)
        client_b = make_client(categories=categories, user_id=user_b)
        category_id = client_a.post("/api/categories", json=category_payload()).json()["id"]

        response = client_b.delete(f"/api/categories/{category_id}")

        assert response.status_code == 404
        assert client_a.get(f"/api/categories/{category_id}").status_code == 200

    async def test_list_does_not_contain_other_users_categories(self) -> None:
        categories = InMemoryCategoryRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(categories=categories, user_id=user_a)
        client_b = make_client(categories=categories, user_id=user_b)
        client_a.post("/api/categories", json=category_payload(name="Категория A"))

        response = client_b.get("/api/categories")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_same_name_same_type_does_not_conflict_between_users(self) -> None:
        categories = InMemoryCategoryRepository()
        user_a, user_b = uuid4(), uuid4()
        client_a = make_client(categories=categories, user_id=user_a)
        client_b = make_client(categories=categories, user_id=user_b)
        client_a.post("/api/categories", json=category_payload(type="income", name="Зарплата"))

        response = client_b.post("/api/categories", json=category_payload(type="income", name="Зарплата"))

        assert response.status_code == 201
