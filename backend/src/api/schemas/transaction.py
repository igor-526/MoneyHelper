from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.entities import CategoryType
from core.schemas import Money, PageParams


class TransactionCreate(BaseModel):
    wallet_id: UUID
    category_id: UUID
    currency_id: UUID
    amount: Money = Field(gt=0)
    occurred_at: datetime | None = None


TransactionUpdate = TransactionCreate


class TransactionLegIn(BaseModel):
    currency_id: UUID
    amount: Money = Field(gt=0)


class TopupCreate(BaseModel):
    wallet_id: UUID
    category_id: UUID
    legs: list[TransactionLegIn]
    occurred_at: datetime | None = None


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
    created_at: datetime
    updated_at: datetime | None


class TransactionListParams(PageParams):
    """`PageParams` с фильтрами списка операций.

    FastAPI разворачивает Pydantic-модель в отдельные query-параметры только когда она — единственный
    query-параметр обработчика, поэтому фильтры включены в саму модель пагинации (см. `CategoryListParams`).
    """

    wallet_id: UUID | None = None
    category_id: UUID | None = None
    type: CategoryType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
