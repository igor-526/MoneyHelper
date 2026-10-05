from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from core.protocols import Clock, CurrencyRepository, IdGenerator, WalletCounter, WorkspaceRepository
from core.services.workspace import WorkspaceService
from depends.auth import get_current_user
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator
from depends.wallet import get_wallet_repository
from repositories.workspace import WorkspaceRepository as SqlWorkspaceRepository
from utils.database import get_session

NOT_FOUND_MESSAGE = "Воркспейс не найден"


def get_workspace_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> WorkspaceRepository:
    return SqlWorkspaceRepository(session)


def get_workspace_service(
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    wallets: Annotated[WalletCounter, Depends(get_wallet_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> WorkspaceService:
    return WorkspaceService(workspaces, currencies, wallets, clock, ids)


async def require_workspace(
    workspace_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> UUID:
    """Проверяет, что `workspace_id` из пути принадлежит текущему пользователю, и возвращает его.

    Используется вместо `get_current_user` во всех роутерах, вложенных под `/api/workspaces/{workspace_id}`.
    """
    workspace = await workspaces.get_by_id(workspace_id, user_id)
    if workspace is None:
        raise NotFoundError(NOT_FOUND_MESSAGE)
    return workspace_id
