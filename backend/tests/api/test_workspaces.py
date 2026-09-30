from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from depends.auth import get_current_user
from depends.workspace import get_workspace_repository
from main import create_app
from tests.fakes import InMemoryWorkspaceRepository


def make_client(
    *,
    workspaces: InMemoryWorkspaceRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> tuple[TestClient, UUID]:
    workspaces = workspaces if workspaces is not None else InMemoryWorkspaceRepository()
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app), user_id


def workspace_payload(name: str = "Поездка в Китай") -> dict:
    return {"name": name}


async def test_create_workspace() -> None:
    client, _ = make_client()

    response = client.post("/api/workspaces", json=workspace_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Поездка в Китай"
    assert body["created_at"] is not None
    assert body["updated_at"] is None


async def test_create_workspace_rejects_empty_name() -> None:
    client, _ = make_client()

    response = client.post("/api/workspaces", json=workspace_payload(name="   "))

    assert response.status_code == 400


async def test_create_workspace_without_session_is_401() -> None:
    client, _ = make_client(authenticated=False)

    response = client.post("/api/workspaces", json=workspace_payload())

    assert response.status_code == 401


async def test_get_list_put_delete_full_cycle() -> None:
    workspaces = InMemoryWorkspaceRepository()
    client, _ = make_client(workspaces=workspaces)

    created = client.post("/api/workspaces", json=workspace_payload()).json()
    workspace_id = created["id"]

    got = client.get(f"/api/workspaces/{workspace_id}")
    assert got.status_code == 200
    assert got.json()["id"] == workspace_id

    listed = client.get("/api/workspaces")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == workspace_id

    updated = client.put(f"/api/workspaces/{workspace_id}", json=workspace_payload(name="Обновлённая поездка"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Обновлённая поездка"
    assert updated.json()["updated_at"] is not None

    deleted = client.delete(f"/api/workspaces/{workspace_id}")
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/workspaces/{workspace_id}")
    assert after_delete.status_code == 404


async def test_get_unknown_workspace_returns_404() -> None:
    client, _ = make_client()

    response = client.get(f"/api/workspaces/{uuid4()}")

    assert response.status_code == 404


async def test_put_unknown_workspace_returns_404() -> None:
    client, _ = make_client()

    response = client.put(f"/api/workspaces/{uuid4()}", json=workspace_payload())

    assert response.status_code == 404


async def test_delete_unknown_workspace_returns_404() -> None:
    client, _ = make_client()

    response = client.delete(f"/api/workspaces/{uuid4()}")

    assert response.status_code == 404


class TestUserIsolation:
    async def test_foreign_workspace_is_not_readable(self) -> None:
        workspaces = InMemoryWorkspaceRepository()
        client_a, _ = make_client(workspaces=workspaces)
        client_b, _ = make_client(workspaces=workspaces)
        workspace_id = client_a.post("/api/workspaces", json=workspace_payload()).json()["id"]

        response = client_b.get(f"/api/workspaces/{workspace_id}")

        assert response.status_code == 404

    async def test_foreign_workspace_is_not_updatable(self) -> None:
        workspaces = InMemoryWorkspaceRepository()
        client_a, _ = make_client(workspaces=workspaces)
        client_b, _ = make_client(workspaces=workspaces)
        workspace_id = client_a.post("/api/workspaces", json=workspace_payload()).json()["id"]

        response = client_b.put(f"/api/workspaces/{workspace_id}", json=workspace_payload(name="Чужое"))

        assert response.status_code == 404
        assert client_a.get(f"/api/workspaces/{workspace_id}").json()["name"] == "Поездка в Китай"

    async def test_foreign_workspace_is_not_deletable(self) -> None:
        workspaces = InMemoryWorkspaceRepository()
        client_a, _ = make_client(workspaces=workspaces)
        client_b, _ = make_client(workspaces=workspaces)
        workspace_id = client_a.post("/api/workspaces", json=workspace_payload()).json()["id"]

        response = client_b.delete(f"/api/workspaces/{workspace_id}")

        assert response.status_code == 404
        assert client_a.get(f"/api/workspaces/{workspace_id}").status_code == 200

    async def test_list_does_not_contain_other_users_workspaces(self) -> None:
        workspaces = InMemoryWorkspaceRepository()
        client_a, _ = make_client(workspaces=workspaces)
        client_b, _ = make_client(workspaces=workspaces)
        client_a.post("/api/workspaces", json=workspace_payload(name="Воркспейс A"))

        response = client_b.get("/api/workspaces")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0
