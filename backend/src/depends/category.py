from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import CategoryRepository, Clock, IdGenerator
from core.services.category import CategoryService
from depends.providers import get_clock, get_id_generator
from repositories.category import CategoryRepository as SqlCategoryRepository
from utils.database import get_session


def get_category_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> CategoryRepository:
    return SqlCategoryRepository(session)


def get_category_service(
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> CategoryService:
    return CategoryService(categories, clock, ids)
