from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel

from core.entities import CategoryType
from core.schemas import Money


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Неизвестный часовой пояс") from error
    return value


class AnalyticsQueryParams(BaseModel):
    display_currency: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    group_by: Literal["wallet", "category", "currency", "day"]
    timezone: Annotated[str, AfterValidator(_check_timezone)] = "UTC"
    wallet_id: UUID | None = None
    category_id: UUID | None = None
    currency_id: UUID | None = None
    type: CategoryType | None = None


class AnalyticsBucketOut(BaseModel):
    group_key: UUID | date
    income: Money
    expense: Money


class AnalyticsOut(BaseModel):
    display_currency_id: UUID
    buckets: list[AnalyticsBucketOut]
    unconverted_currencies: list[UUID]
