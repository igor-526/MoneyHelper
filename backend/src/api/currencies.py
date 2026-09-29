from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.schemas.currency import CurrencyOut
from core.schemas import Page, PageParams
from core.services.currency import CurrencyService
from depends.currency import get_currency_service

router = APIRouter(prefix="/api/currencies", tags=["Currencies"])


@router.get("", response_model=Page[CurrencyOut])
async def list_currencies(
    params: Annotated[PageParams, Query()],
    currency_service: Annotated[CurrencyService, Depends(get_currency_service)],
) -> Page[CurrencyOut]:
    items, total = await currency_service.list_currencies(limit=params.limit, offset=params.offset)
    return Page[CurrencyOut](
        items=[CurrencyOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )
