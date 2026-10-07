from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.schemas.analytics import (
    AnalyticsBucketOut,
    AnalyticsOut,
    AnalyticsQueryParams,
    ExchangeRateHistoryOut,
    ExchangeRateHistoryQueryParams,
    ExchangeRatePointOut,
)
from core.services.analytics import AnalyticsService
from core.services.exchange_rate_history import ExchangeRateHistoryService
from depends.analytics import get_analytics_service, get_exchange_rate_history_service
from depends.workspace import require_workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}/analytics", tags=["Analytics"])


@router.get("/rates", response_model=ExchangeRateHistoryOut)
async def get_exchange_rate_history(
    params: Annotated[ExchangeRateHistoryQueryParams, Query()],
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    service: Annotated[ExchangeRateHistoryService, Depends(get_exchange_rate_history_service)],
) -> ExchangeRateHistoryOut:
    history = await service.get_history(
        workspace_id,
        base_currency_id=params.currency_id,
        date_from=params.date_from,
        date_to=params.date_to,
    )
    return ExchangeRateHistoryOut(
        base_currency_id=history.base_currency_id,
        quote_currency_id=history.quote_currency_id,
        points=[ExchangeRatePointOut(date=point.date, rate=point.rate) for point in history.points],
    )


@router.get("", response_model=AnalyticsOut)
async def get_analytics(
    params: Annotated[AnalyticsQueryParams, Query()],
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AnalyticsOut:
    display_currency_id, buckets, unconverted = await analytics_service.get_analytics(
        workspace_id,
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
        display_currency_id=display_currency_id,
        buckets=[
            AnalyticsBucketOut(group_key=key, income=income, expense=expense) for key, income, expense in buckets
        ],
        unconverted_currencies=unconverted,
    )
