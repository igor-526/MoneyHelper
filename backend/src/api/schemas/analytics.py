from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from core.entities import CategoryType
from core.schemas import Money


class AnalyticsQueryParams(BaseModel):
    display_currency: UUID | None = None
    date_from: datetime
    date_to: datetime
    group_by: Literal["wallet", "category", "currency"]
    wallet_id: UUID | None = None
    category_id: UUID | None = None
    currency_id: UUID | None = None
    type: CategoryType | None = None


class AnalyticsBucketOut(BaseModel):
    group_key: UUID
    income: Money
    expense: Money


class AnalyticsOut(BaseModel):
    display_currency_id: UUID
    buckets: list[AnalyticsBucketOut]
    unconverted_currencies: list[UUID]
