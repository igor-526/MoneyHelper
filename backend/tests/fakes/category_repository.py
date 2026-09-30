from datetime import datetime
from uuid import UUID

from core.entities import Category, CategoryType
from core.exceptions import AlreadyExistsError


class InMemoryCategoryRepository:
    def __init__(self) -> None:
        self._categories: dict[UUID, Category] = {}

    async def add(self, category: Category) -> Category:
        self._check_duplicate(category.workspace_id, category.type, category.name, exclude_id=None)
        self._categories[category.id] = category
        return category

    async def get_by_id(self, category_id: UUID, workspace_id: UUID) -> Category | None:
        category = self._categories.get(category_id)
        return category if category is not None and category.workspace_id == workspace_id else None

    async def list(self, workspace_id: UUID, *, type: CategoryType | None, limit: int, offset: int) -> list[Category]:
        items = sorted(
            (
                category
                for category in self._categories.values()
                if category.workspace_id == workspace_id and (type is None or category.type == type)
            ),
            key=lambda category: (category.created_at, category.id),
        )
        return items[offset : offset + limit]

    async def count(self, workspace_id: UUID, *, type: CategoryType | None) -> int:
        return sum(
            1
            for category in self._categories.values()
            if category.workspace_id == workspace_id and (type is None or category.type == type)
        )

    async def update(
        self, category_id: UUID, workspace_id: UUID, *, type: CategoryType, name: str, icon: str, now: datetime
    ) -> Category | None:
        category = self._categories.get(category_id)
        if category is None or category.workspace_id != workspace_id:
            return None
        self._check_duplicate(workspace_id, type, name, exclude_id=category_id)
        updated = category.model_copy(update={"type": type, "name": name, "icon": icon, "updated_at": now})
        self._categories[category_id] = updated
        return updated

    async def delete(self, category_id: UUID, workspace_id: UUID) -> bool:
        category = self._categories.get(category_id)
        if category is None or category.workspace_id != workspace_id:
            return False
        del self._categories[category_id]
        return True

    def _check_duplicate(self, workspace_id: UUID, type: CategoryType, name: str, *, exclude_id: UUID | None) -> None:
        for category in self._categories.values():
            same_owner_type_name = (
                category.workspace_id == workspace_id and category.type == type and category.name == name
            )
            if category.id != exclude_id and same_owner_type_name:
                raise AlreadyExistsError("Категория с таким названием уже существует среди категорий этого типа")
