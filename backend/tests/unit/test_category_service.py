from uuid import uuid4

import pytest

from core.entities import CategoryType
from core.exceptions import AlreadyExistsError, NotFoundError
from core.services.category import CategoryService
from tests.fakes import FixedClock, InMemoryCategoryRepository, SequentialIdGenerator


def make_service() -> tuple[CategoryService, InMemoryCategoryRepository]:
    categories = InMemoryCategoryRepository()
    service = CategoryService(categories, FixedClock(), SequentialIdGenerator())
    return service, categories


async def test_create_income_category() -> None:
    service, _ = make_service()
    user_id = uuid4()

    category = await service.create_category(user_id, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    assert category.user_id == user_id
    assert category.type == CategoryType.INCOME
    assert category.name == "Зарплата"
    assert category.icon == "wallet"
    assert category.created_at is not None


async def test_create_expense_category() -> None:
    service, _ = make_service()
    user_id = uuid4()

    category = await service.create_category(user_id, type=CategoryType.EXPENSE, name="Продукты", icon="banknote")

    assert category.type == CategoryType.EXPENSE


async def test_create_category_duplicate_name_within_type_raises_already_exists() -> None:
    service, _ = make_service()
    user_id = uuid4()
    await service.create_category(user_id, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    with pytest.raises(AlreadyExistsError):
        await service.create_category(user_id, type=CategoryType.INCOME, name="Зарплата", icon="wallet")


async def test_create_category_same_name_different_type_is_allowed() -> None:
    service, _ = make_service()
    user_id = uuid4()
    await service.create_category(user_id, type=CategoryType.INCOME, name="Прочее", icon="wallet")

    category = await service.create_category(user_id, type=CategoryType.EXPENSE, name="Прочее", icon="wallet")

    assert category.type == CategoryType.EXPENSE


async def test_get_category_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.get_category(uuid4(), uuid4())


async def test_get_category_belonging_to_another_user_raises_not_found() -> None:
    service, _ = make_service()
    owner = uuid4()
    category = await service.create_category(owner, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    with pytest.raises(NotFoundError):
        await service.get_category(category.id, uuid4())


async def test_update_category_replaces_type_name_and_icon() -> None:
    service, _ = make_service()
    owner = uuid4()
    category = await service.create_category(owner, type=CategoryType.INCOME, name="Старое", icon="wallet")

    updated = await service.update_category(
        category.id, owner, type=CategoryType.EXPENSE, name="Новое", icon="banknote"
    )

    assert updated.type == CategoryType.EXPENSE
    assert updated.name == "Новое"
    assert updated.icon == "banknote"
    assert updated.updated_at is not None


async def test_update_category_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.update_category(uuid4(), uuid4(), type=CategoryType.INCOME, name="X", icon="wallet")


async def test_update_category_belonging_to_another_user_raises_not_found() -> None:
    service, _ = make_service()
    owner = uuid4()
    category = await service.create_category(owner, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    with pytest.raises(NotFoundError):
        await service.update_category(category.id, uuid4(), type=CategoryType.INCOME, name="X", icon="wallet")


async def test_update_category_duplicate_name_raises_already_exists() -> None:
    service, _ = make_service()
    owner = uuid4()
    await service.create_category(owner, type=CategoryType.INCOME, name="A", icon="wallet")
    category_b = await service.create_category(owner, type=CategoryType.INCOME, name="B", icon="wallet")

    with pytest.raises(AlreadyExistsError):
        await service.update_category(category_b.id, owner, type=CategoryType.INCOME, name="A", icon="wallet")


async def test_delete_category_unknown_id_raises_not_found() -> None:
    service, _ = make_service()

    with pytest.raises(NotFoundError):
        await service.delete_category(uuid4(), uuid4())


async def test_delete_category_belonging_to_another_user_raises_not_found() -> None:
    service, _ = make_service()
    owner = uuid4()
    category = await service.create_category(owner, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    with pytest.raises(NotFoundError):
        await service.delete_category(category.id, uuid4())


async def test_delete_category_success() -> None:
    service, categories = make_service()
    owner = uuid4()
    category = await service.create_category(owner, type=CategoryType.INCOME, name="Зарплата", icon="wallet")

    await service.delete_category(category.id, owner)

    assert await categories.get_by_id(category.id, owner) is None


async def test_list_categories_returns_only_given_user_categories() -> None:
    service, _ = make_service()
    user_a, user_b = uuid4(), uuid4()
    await service.create_category(user_a, type=CategoryType.INCOME, name="A1", icon="wallet")
    await service.create_category(user_b, type=CategoryType.INCOME, name="B1", icon="wallet")

    items, total = await service.list_categories(user_a, type=None, limit=20, offset=0)

    assert total == 1
    assert [category.name for category in items] == ["A1"]


async def test_list_categories_filters_by_type() -> None:
    service, _ = make_service()
    user_id = uuid4()
    await service.create_category(user_id, type=CategoryType.INCOME, name="Зарплата", icon="wallet")
    await service.create_category(user_id, type=CategoryType.EXPENSE, name="Продукты", icon="banknote")

    items, total = await service.list_categories(user_id, type=CategoryType.INCOME, limit=20, offset=0)

    assert total == 1
    assert [category.name for category in items] == ["Зарплата"]


async def test_list_categories_without_filter_returns_both_types() -> None:
    service, _ = make_service()
    user_id = uuid4()
    await service.create_category(user_id, type=CategoryType.INCOME, name="Зарплата", icon="wallet")
    await service.create_category(user_id, type=CategoryType.EXPENSE, name="Продукты", icon="banknote")

    items, total = await service.list_categories(user_id, type=None, limit=20, offset=0)

    assert total == 2
