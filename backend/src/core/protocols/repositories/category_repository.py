from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.entities import Category, CategoryType


class CategoryRepository(Protocol):
    async def add(self, category: Category) -> Category: ...

    async def get_by_id(self, category_id: UUID, user_id: UUID) -> Category | None: ...

    async def list(self, user_id: UUID, *, type: CategoryType | None, limit: int, offset: int) -> list[Category]: ...

    async def count(self, user_id: UUID, *, type: CategoryType | None) -> int: ...

    async def update(
        self, category_id: UUID, user_id: UUID, *, type: CategoryType, name: str, icon: str, now: datetime
    ) -> Category | None: ...

    async def delete(self, category_id: UUID, user_id: UUID) -> bool: ...
