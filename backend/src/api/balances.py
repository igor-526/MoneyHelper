from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from api.schemas.balance import WalletBalanceOut
from core.services.balance import BalanceService
from depends.balance import get_balance_service
from depends.workspace import require_workspace

wallet_balances_router = APIRouter(tags=["Transactions"])


@wallet_balances_router.get(
    "/api/workspaces/{workspace_id}/wallets/{wallet_id}/balances", response_model=list[WalletBalanceOut]
)
async def get_wallet_balances(
    wallet_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    balance_service: Annotated[BalanceService, Depends(get_balance_service)],
) -> list[WalletBalanceOut]:
    balances = await balance_service.get_wallet_balances(wallet_id, workspace_id)
    return [WalletBalanceOut(currency_id=currency_id, balance=balance) for currency_id, balance in balances]
