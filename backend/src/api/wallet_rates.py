from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.schemas.wallet_rate import CurrencyRateOut, WalletRatesOut
from core.services.wallet_rate import WalletRateService
from depends.wallet_rate import get_wallet_rate_service
from depends.workspace import require_workspace

wallet_rates_router = APIRouter(tags=["Wallets"])


@wallet_rates_router.get("/api/workspaces/{workspace_id}/wallets/{wallet_id}/rates", response_model=WalletRatesOut)
async def get_wallet_rates(
    wallet_id: UUID,
    target_currency_id: Annotated[UUID, Query()],
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    wallet_rate_service: Annotated[WalletRateService, Depends(get_wallet_rate_service)],
) -> WalletRatesOut:
    result = await wallet_rate_service.get_wallet_rates(wallet_id, workspace_id, target_currency_id=target_currency_id)
    return WalletRatesOut(
        target_currency_id=result.target_currency_id,
        rates=[CurrencyRateOut(currency_id=currency_id, rate=rate) for currency_id, rate in result.rates.items()],
        unrated_currency_ids=result.unrated_currency_ids,
    )
