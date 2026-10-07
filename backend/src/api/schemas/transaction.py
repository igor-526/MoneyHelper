from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schemas import Money, PageParams

COMMENT_MAX_LENGTH = 1000


def normalize_comment_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wallet_id: UUID
    category_id: UUID
    amount: Money = Field(gt=0)
    occurred_at: datetime | None = None
    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        return normalize_comment_text(value)

    @field_validator("occurred_at")
    @classmethod
    def ensure_local_occurred_at(cls, value: datetime | None) -> datetime | None:
        from api.schemas.local_datetime import validate_local_datetime

        return validate_local_datetime(value)


TransactionUpdate = TransactionCreate


class TransactionLegOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency_id: UUID
    amount: Money


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wallet_id: UUID
    category_id: UUID
    legs: list[TransactionLegOut]
    occurred_at: datetime
    comment: str | None
    created_at: datetime
    updated_at: datetime | None


class TransactionListParams(PageParams):
    """`PageParams` с фильтрами списка операций.

    FastAPI разворачивает Pydantic-модель в отдельные query-параметры только когда она — единственный
    query-параметр обработчика, поэтому фильтры включены в саму модель пагинации (см. `CategoryListParams`).
    """

    wallet_id: UUID | None = None
    category_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None

    @field_validator("date_from", "date_to")
    @classmethod
    def ensure_local_range(cls, value: datetime | None) -> datetime | None:
        from api.schemas.local_datetime import validate_local_datetime

        return validate_local_datetime(value)
