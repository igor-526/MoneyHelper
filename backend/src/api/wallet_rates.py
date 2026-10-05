from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from api.schemas.wallet_rate import WalletRateOut
from core.services.wallet_rate import WalletRateService
from depends.wallet_rate import get_wallet_rate_service
from depends.workspace import require_workspace

wallet_rates_router = APIRouter(tags=["Wallets"])


@wallet_rates_router.get("/api/workspaces/{workspace_id}/wallets/{wallet_id}/rates", response_model=WalletRateOut)
async def get_wallet_rate(
    wallet_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    wallet_rate_service: Annotated[WalletRateService, Depends(get_wallet_rate_service)],
) -> WalletRateOut:
    return WalletRateOut.model_validate(await wallet_rate_service.get_wallet_rate(wallet_id, workspace_id))
