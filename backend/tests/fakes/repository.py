from uuid import UUID

from core.entities import Entity


class InMemoryRepository[T: Entity]:
    """Основа для fake-репозиториев: те же контракты, что у боевых (`get` возвращает None, а не бросает ошибку)."""

    def __init__(self) -> None:
        self._items: dict[UUID, T] = {}

    async def add(self, entity: T) -> T:
        self._items[entity.id] = entity
        return entity

    async def get(self, entity_id: UUID) -> T | None:
        return self._items.get(entity_id)

    async def delete(self, entity_id: UUID) -> bool:
        return self._items.pop(entity_id, None) is not None

    async def list(self, *, limit: int, offset: int) -> list[T]:
        return list(self._items.values())[offset : offset + limit]

    async def count(self) -> int:
        return len(self._items)
