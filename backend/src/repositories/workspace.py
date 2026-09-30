from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Workspace
from models import workspaces


def _map_row(row: Row[Any]) -> Workspace:
    return Workspace(
        id=row.id, user_id=row.user_id, name=row.name, created_at=row.created_at, updated_at=row.updated_at
    )


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> Workspace:
        await self._session.execute(
            insert(workspaces).values(
                id=workspace.id,
                user_id=workspace.user_id,
                name=workspace.name,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )
        )
        return workspace

    async def get_by_id(self, workspace_id: UUID, user_id: UUID) -> Workspace | None:
        row = (
            await self._session.execute(
                select(workspaces).where(workspaces.c.id == workspace_id, workspaces.c.user_id == user_id)
            )
        ).first()
        return _map_row(row) if row is not None else None

    async def list(self, user_id: UUID, *, limit: int, offset: int) -> list[Workspace]:
        rows = (
            await self._session.execute(
                select(workspaces)
                .where(workspaces.c.user_id == user_id)
                .order_by(workspaces.c.created_at, workspaces.c.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [_map_row(row) for row in rows]

    async def count(self, user_id: UUID) -> int:
        return (
            await self._session.execute(
                select(func.count()).select_from(workspaces).where(workspaces.c.user_id == user_id)
            )
        ).scalar_one()

    async def update(self, workspace_id: UUID, user_id: UUID, *, name: str, now: datetime) -> Workspace | None:
        result = await self._session.execute(
            sa_update(workspaces)
            .where(workspaces.c.id == workspace_id, workspaces.c.user_id == user_id)
            .values(name=name, updated_at=now)
            .returning(workspaces)
        )
        row = result.first()
        return _map_row(row) if row is not None else None

    async def delete(self, workspace_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            sa_delete(workspaces)
            .where(workspaces.c.id == workspace_id, workspaces.c.user_id == user_id)
            .returning(workspaces.c.id)
        )
        return result.first() is not None
