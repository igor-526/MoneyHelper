from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.entities import CategoryType
from core.schemas import IconName, PageParams


class CategoryCreate(BaseModel):
    type: CategoryType
    name: str = Field(min_length=1, max_length=100)
    icon: IconName

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name не может быть пустым")
        return stripped


CategoryUpdate = CategoryCreate


class CategoryListParams(PageParams):
    """`PageParams` с добавленным фильтром по типу.

    FastAPI разворачивает Pydantic-модель в отдельные query-параметры только когда она — единственный
    query-параметр обработчика (см. `fastapi.dependencies.utils._get_flat_fields_from_params`). Отдельный
    `type: CategoryType | None` рядом с `Annotated[PageParams, Query()]` в сигнатуре эндпоинта ломает это
    разворачивание, поэтому фильтр включён в саму модель пагинации.
    """

    type: CategoryType | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: CategoryType
    name: str
    icon: str
    created_at: datetime
    updated_at: datetime | None
