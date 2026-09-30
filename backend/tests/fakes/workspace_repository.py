from datetime import datetime
from uuid import UUID

from core.entities import Workspace


class InMemoryWorkspaceRepository:
    def __init__(self) -> None:
        self._workspaces: dict[UUID, Workspace] = {}

    async def add(self, workspace: Workspace) -> Workspace:
        self._workspaces[workspace.id] = workspace
        return workspace

    def seed(self, workspace: Workspace) -> None:
        """Синхронно кладёт воркспейс в фейк — удобно в тестах других роутеров, которым не нужен async."""
        self._workspaces[workspace.id] = workspace

    async def get_by_id(self, workspace_id: UUID, user_id: UUID) -> Workspace | None:
        workspace = self._workspaces.get(workspace_id)
        return workspace if workspace is not None and workspace.user_id == user_id else None

    async def list(self, user_id: UUID, *, limit: int, offset: int) -> list[Workspace]:
        items = sorted(
            (workspace for workspace in self._workspaces.values() if workspace.user_id == user_id),
            key=lambda workspace: (workspace.created_at, workspace.id),
        )
        return items[offset : offset + limit]

    async def count(self, user_id: UUID) -> int:
        return sum(1 for workspace in self._workspaces.values() if workspace.user_id == user_id)

    async def update(self, workspace_id: UUID, user_id: UUID, *, name: str, now: datetime) -> Workspace | None:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None or workspace.user_id != user_id:
            return None
        updated = workspace.model_copy(update={"name": name, "updated_at": now})
        self._workspaces[workspace_id] = updated
        return updated

    async def delete(self, workspace_id: UUID, user_id: UUID) -> bool:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None or workspace.user_id != user_id:
            return False
        del self._workspaces[workspace_id]
        return True
