from uuid import uuid4

import pytest

from core.exceptions import NotFoundError
from core.services.workspace import WorkspaceService
from tests.fakes import FixedClock, InMemoryWorkspaceRepository, SequentialIdGenerator


def make_service() -> tuple[WorkspaceService, InMemoryWorkspaceRepository]:
    workspaces = InMemoryWorkspaceRepository()
    service = WorkspaceService(workspaces, FixedClock(), SequentialIdGenerator())
    return service, workspaces


async def test_create_workspace() -> None:
    service, _ = make_service()
    user_id = uuid4()

    workspace = await service.create_workspace(user_id, name="Поездка в Китай")

    assert workspace.user_id == user_id
    assert workspace.name == "Поездка в Китай"
    assert workspace.created_at is not None


async def test_get_workspace_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_workspace(uuid4(), uuid4())


async def test_get_workspace_belonging_to_another_user_raises_not_found() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка")

    with pytest.raises(NotFoundError):
        await service.get_workspace(workspace.id, uuid4())


async def test_update_workspace() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка")

    updated = await service.update_workspace(workspace.id, owner, name="Новое название")

    assert updated.name == "Новое название"
    assert updated.updated_at is not None


async def test_update_workspace_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.update_workspace(uuid4(), uuid4(), name="X")


async def test_delete_workspace_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.delete_workspace(uuid4(), uuid4())


async def test_delete_workspace_success() -> None:
    service, workspaces = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка")

    await service.delete_workspace(workspace.id, owner)

    assert await workspaces.get_by_id(workspace.id, owner) is None


async def test_delete_workspace_does_not_check_for_related_data() -> None:
    """В отличие от кошелька/категории, удаление воркспейса не проверяет наличие вложенных данных — каскад на БД."""
    service, workspaces = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка")

    await service.delete_workspace(workspace.id, owner)

    assert await workspaces.get_by_id(workspace.id, owner) is None


async def test_list_workspaces_returns_only_given_user_workspaces() -> None:
    service, _ = make_service()
    user_a, user_b = uuid4(), uuid4()
    await service.create_workspace(user_a, name="A1")
    await service.create_workspace(user_b, name="B1")

    items, total = await service.list_workspaces(user_a, limit=20, offset=0)

    assert total == 1
    assert [workspace.name for workspace in items] == ["A1"]
