from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.category import CategoryCreate, CategoryListParams, CategoryOut, CategoryUpdate
from core.schemas import Page
from core.services.category import CategoryService
from depends.auth import get_current_user
from depends.category import get_category_service

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryOut:
    category = await category_service.create_category(user_id, type=body.type, name=body.name, icon=body.icon)
    return CategoryOut.model_validate(category)


@router.get("", response_model=Page[CategoryOut])
async def list_categories(
    params: Annotated[CategoryListParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> Page[CategoryOut]:
    items, total = await category_service.list_categories(
        user_id, type=params.type, limit=params.limit, offset=params.offset
    )
    return Page[CategoryOut](
        items=[CategoryOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryOut:
    category = await category_service.get_category(category_id, user_id)
    return CategoryOut.model_validate(category)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryOut:
    category = await category_service.update_category(
        category_id, user_id, type=body.type, name=body.name, icon=body.icon
    )
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> None:
    await category_service.delete_category(category_id, user_id)
