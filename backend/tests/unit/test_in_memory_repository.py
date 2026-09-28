from uuid import UUID

from core.entities import Entity
from tests.fakes import InMemoryRepository, SequentialIdGenerator


def _entities(count: int) -> list[Entity]:
    ids = SequentialIdGenerator()
    return [Entity(id=ids.new()) for _ in range(count)]


async def test_get_missing_returns_none() -> None:
    repository = InMemoryRepository[Entity]()

    assert await repository.get(UUID(int=42)) is None


async def test_add_and_get() -> None:
    repository = InMemoryRepository[Entity]()
    entity = _entities(1)[0]

    await repository.add(entity)

    assert await repository.get(entity.id) == entity


async def test_list_with_slice_keeps_insertion_order() -> None:
    repository = InMemoryRepository[Entity]()
    first, second, third = _entities(3)
    for entity in (first, second, third):
        await repository.add(entity)

    assert await repository.list(limit=2, offset=1) == [second, third]
    assert await repository.count() == 3


async def test_delete_reports_whether_entity_existed() -> None:
    repository = InMemoryRepository[Entity]()
    entity = _entities(1)[0]
    await repository.add(entity)

    assert await repository.delete(entity.id) is True
    assert await repository.delete(entity.id) is False
    assert await repository.get(entity.id) is None
