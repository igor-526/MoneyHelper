from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType
from core.exceptions import AlreadyExistsError, ConflictError
from models import categories

DUPLICATE_NAME_MESSAGE = "Категория с таким названием уже существует среди категорий этого типа"
DELETE_CONFLICT_MESSAGE = "Категорию нельзя удалить: есть операции"


def _map_row(row: Row[Any]) -> Category:
    return Category(
        id=row.id,
        workspace_id=row.workspace_id,
        type=row.type,
        name=row.name,
        icon=row.icon,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, category: Category) -> Category:
        try:
            await self._session.execute(
                insert(categories).values(
                    id=category.id,
                    workspace_id=category.workspace_id,
                    type=category.type,
                    name=category.name,
                    icon=category.icon,
                    created_at=category.created_at,
                    updated_at=category.updated_at,
                )
            )
        except IntegrityError as exc:
            raise AlreadyExistsError(DUPLICATE_NAME_MESSAGE) from exc
        return category

    async def get_by_id(self, category_id: UUID, workspace_id: UUID) -> Category | None:
        row = (
            await self._session.execute(
                select(categories).where(categories.c.id == category_id, categories.c.workspace_id == workspace_id)
            )
        ).first()
        return _map_row(row) if row is not None else None

    async def list(self, workspace_id: UUID, *, type: CategoryType | None, limit: int, offset: int) -> list[Category]:
        query = select(categories).where(categories.c.workspace_id == workspace_id)
        if type is not None:
            query = query.where(categories.c.type == type)
        rows = (
            await self._session.execute(
                query.order_by(categories.c.created_at, categories.c.id).limit(limit).offset(offset)
            )
        ).all()
        return [_map_row(row) for row in rows]

    async def count(self, workspace_id: UUID, *, type: CategoryType | None) -> int:
        query = select(func.count()).select_from(categories).where(categories.c.workspace_id == workspace_id)
        if type is not None:
            query = query.where(categories.c.type == type)
        return (await self._session.execute(query)).scalar_one()

    async def update(
        self, category_id: UUID, workspace_id: UUID, *, type: CategoryType, name: str, icon: str, now: datetime
    ) -> Category | None:
        try:
            result = await self._session.execute(
                sa_update(categories)
                .where(categories.c.id == category_id, categories.c.workspace_id == workspace_id)
                .values(type=type, name=name, icon=icon, updated_at=now)
                .returning(categories)
            )
        except IntegrityError as exc:
            raise AlreadyExistsError(DUPLICATE_NAME_MESSAGE) from exc
        row = result.first()
        return _map_row(row) if row is not None else None

    async def delete(self, category_id: UUID, workspace_id: UUID) -> bool:
        try:
            result = await self._session.execute(
                sa_delete(categories)
                .where(categories.c.id == category_id, categories.c.workspace_id == workspace_id)
                .returning(categories.c.id)
            )
        except IntegrityError as exc:
            raise ConflictError(DELETE_CONFLICT_MESSAGE) from exc
        return result.first() is not None
