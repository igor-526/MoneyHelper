from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.schemas.analytics import AnalyticsBucketOut, AnalyticsOut, AnalyticsQueryParams
from core.services.analytics import AnalyticsService
from depends.analytics import get_analytics_service
from depends.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsOut)
async def get_analytics(
    params: Annotated[AnalyticsQueryParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AnalyticsOut:
    buckets, unconverted = await analytics_service.get_analytics(
        user_id,
        display_currency_id=params.display_currency,
        date_from=params.date_from,
        date_to=params.date_to,
        group_by=params.group_by,
        wallet_id=params.wallet_id,
        category_id=params.category_id,
        currency_id=params.currency_id,
        type=params.type,
    )
    return AnalyticsOut(
        display_currency_id=params.display_currency,
        buckets=[
            AnalyticsBucketOut(group_key=key, income=income, expense=expense) for key, income, expense in buckets
        ],
        unconverted_currencies=unconverted,
    )
