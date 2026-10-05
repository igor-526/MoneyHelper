from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from core.entities import Currency, Wallet
from core.exceptions import ClientError, ConflictError, NotFoundError
from core.services.workspace import WorkspaceService
from tests.fakes import (
    FixedClock,
    InMemoryCurrencyRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
    SequentialIdGenerator,
)

RUB = Currency(id=uuid4(), code="RUB", name="Российский рубль", decimal_places=2)
CNY = Currency(id=uuid4(), code="CNY", name="Китайский юань", decimal_places=2)


def make_service() -> tuple[WorkspaceService, InMemoryWorkspaceRepository]:
    service, workspaces, _ = make_service_with_wallets()
    return service, workspaces


def make_service_with_wallets() -> tuple[WorkspaceService, InMemoryWorkspaceRepository, InMemoryWalletRepository]:
    workspaces = InMemoryWorkspaceRepository()
    wallets = InMemoryWalletRepository()
    currencies = InMemoryCurrencyRepository()
    currencies._currencies = {RUB.id: RUB, CNY.id: CNY}
    service = WorkspaceService(workspaces, currencies, wallets, FixedClock(), SequentialIdGenerator())
    return service, workspaces, wallets


async def add_wallet(wallets: InMemoryWalletRepository, workspace_id: UUID) -> None:
    await wallets.add(
        Wallet(
            id=uuid4(),
            workspace_id=workspace_id,
            name="Наличные",
            icon="wallet",
            currency_id=RUB.id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )


async def test_create_workspace() -> None:
    service, _ = make_service()
    user_id = uuid4()

    workspace = await service.create_workspace(user_id, name="Поездка в Китай", currency_id=RUB.id)

    assert workspace.user_id == user_id
    assert workspace.name == "Поездка в Китай"
    assert workspace.currency_id == RUB.id
    assert workspace.created_at is not None


async def test_create_workspace_unknown_currency_raises_client_error() -> None:
    service, workspaces = make_service()
    user_id = uuid4()

    with pytest.raises(ClientError):
        await service.create_workspace(user_id, name="Поездка", currency_id=uuid4())

    assert await workspaces.count(user_id) == 0


async def test_get_workspace_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_workspace(uuid4(), uuid4())


async def test_get_workspace_belonging_to_another_user_raises_not_found() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    with pytest.raises(NotFoundError):
        await service.get_workspace(workspace.id, uuid4())


async def test_update_workspace() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    updated = await service.update_workspace(workspace.id, owner, name="Новое название")

    assert updated.name == "Новое название"
    assert updated.updated_at is not None


async def test_update_workspace_without_currency_keeps_it() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    updated = await service.update_workspace(workspace.id, owner, name="Новое название")

    assert updated.currency_id == RUB.id


async def test_update_workspace_changes_currency_without_wallets() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    updated = await service.update_workspace(workspace.id, owner, name="Поездка", currency_id=CNY.id)

    assert updated.currency_id == CNY.id


async def test_update_workspace_currency_with_wallets_raises_conflict() -> None:
    service, workspaces, wallets = make_service_with_wallets()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)
    await add_wallet(wallets, workspace.id)

    with pytest.raises(ConflictError):
        await service.update_workspace(workspace.id, owner, name="Другое", currency_id=CNY.id)

    unchanged = await workspaces.get_by_id(workspace.id, owner)
    assert unchanged is not None
    assert (unchanged.name, unchanged.currency_id) == ("Поездка", RUB.id)


async def test_update_workspace_renames_with_wallets_and_same_currency() -> None:
    service, _, wallets = make_service_with_wallets()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)
    await add_wallet(wallets, workspace.id)

    updated = await service.update_workspace(workspace.id, owner, name="Другое", currency_id=RUB.id)

    assert updated.name == "Другое"
    assert updated.currency_id == RUB.id


async def test_update_workspace_unknown_currency_raises_client_error() -> None:
    service, _ = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    with pytest.raises(ClientError):
        await service.update_workspace(workspace.id, owner, name="Поездка", currency_id=uuid4())


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
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    await service.delete_workspace(workspace.id, owner)

    assert await workspaces.get_by_id(workspace.id, owner) is None


async def test_delete_workspace_does_not_check_for_related_data() -> None:
    """В отличие от кошелька/категории, удаление воркспейса не проверяет наличие вложенных данных — каскад на БД."""
    service, workspaces = make_service()
    owner = uuid4()
    workspace = await service.create_workspace(owner, name="Поездка", currency_id=RUB.id)

    await service.delete_workspace(workspace.id, owner)

    assert await workspaces.get_by_id(workspace.id, owner) is None


async def test_list_workspaces_returns_only_given_user_workspaces() -> None:
    service, _ = make_service()
    user_a, user_b = uuid4(), uuid4()
    await service.create_workspace(user_a, name="A1", currency_id=RUB.id)
    await service.create_workspace(user_b, name="B1", currency_id=RUB.id)

    items, total = await service.list_workspaces(user_a, limit=20, offset=0)

    assert total == 1
    assert [workspace.name for workspace in items] == ["A1"]
