from uuid import UUID

from core.entities import Category, CategoryType
from core.exceptions import NotFoundError
from core.protocols import CategoryRepository, Clock, IdGenerator

NOT_FOUND_MESSAGE = "Категория не найдена"


class CategoryService:
    def __init__(self, categories: CategoryRepository, clock: Clock, ids: IdGenerator) -> None:
        self._categories = categories
        self._clock = clock
        self._ids = ids

    async def create_category(self, workspace_id: UUID, *, type: CategoryType, name: str, icon: str) -> Category:
        category = Category(
            id=self._ids.new(),
            workspace_id=workspace_id,
            type=type,
            name=name,
            icon=icon,
            created_at=self._clock.now(),
        )
        return await self._categories.add(category)

    async def get_category(self, category_id: UUID, workspace_id: UUID) -> Category:
        category = await self._categories.get_by_id(category_id, workspace_id)
        if category is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return category

    async def list_categories(
        self, workspace_id: UUID, *, type: CategoryType | None, limit: int, offset: int
    ) -> tuple[list[Category], int]:
        items = await self._categories.list(workspace_id, type=type, limit=limit, offset=offset)
        total = await self._categories.count(workspace_id, type=type)
        return items, total

    async def update_category(
        self, category_id: UUID, workspace_id: UUID, *, type: CategoryType, name: str, icon: str
    ) -> Category:
        category = await self._categories.update(
            category_id, workspace_id, type=type, name=name, icon=icon, now=self._clock.now()
        )
        if category is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return category

    async def delete_category(self, category_id: UUID, workspace_id: UUID) -> None:
        deleted = await self._categories.delete(category_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)
