from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from api.schemas.local_datetime import validate_local_datetime
from core.entities import CategoryType
from core.schemas import Money


class AnalyticsQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_currency: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    group_by: Literal["wallet", "category", "currency", "day"]
    wallet_id: UUID | None = None
    category_id: UUID | None = None
    currency_id: UUID | None = None
    type: CategoryType | None = None

    @field_validator("date_from", "date_to")
    @classmethod
    def ensure_local_range(cls, value: datetime | None) -> datetime | None:
        return validate_local_datetime(value)


class AnalyticsBucketOut(BaseModel):
    group_key: UUID | date
    income: Money
    expense: Money


class AnalyticsOut(BaseModel):
    display_currency_id: UUID
    buckets: list[AnalyticsBucketOut]
    unconverted_currencies: list[UUID]
