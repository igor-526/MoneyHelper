from uuid import UUID

from core.entities import Workspace
from core.exceptions import NotFoundError
from core.protocols import Clock, IdGenerator, WorkspaceRepository

NOT_FOUND_MESSAGE = "Воркспейс не найден"


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository, clock: Clock, ids: IdGenerator) -> None:
        self._workspaces = workspaces
        self._clock = clock
        self._ids = ids

    async def create_workspace(self, user_id: UUID, *, name: str) -> Workspace:
        workspace = Workspace(id=self._ids.new(), user_id=user_id, name=name, created_at=self._clock.now())
        return await self._workspaces.add(workspace)

    async def get_workspace(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id, user_id)
        if workspace is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return workspace

    async def list_workspaces(self, user_id: UUID, *, limit: int, offset: int) -> tuple[list[Workspace], int]:
        items = await self._workspaces.list(user_id, limit=limit, offset=offset)
        total = await self._workspaces.count(user_id)
        return items, total

    async def update_workspace(self, workspace_id: UUID, user_id: UUID, *, name: str) -> Workspace:
        workspace = await self._workspaces.update(workspace_id, user_id, name=name, now=self._clock.now())
        if workspace is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return workspace

    async def delete_workspace(self, workspace_id: UUID, user_id: UUID) -> None:
        deleted = await self._workspaces.delete(workspace_id, user_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)
