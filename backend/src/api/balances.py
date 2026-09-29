from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from api.schemas.balance import WalletBalanceOut
from core.services.balance import BalanceService
from depends.auth import get_current_user
from depends.balance import get_balance_service

wallet_balances_router = APIRouter(tags=["Transactions"])


@wallet_balances_router.get("/api/wallets/{wallet_id}/balances", response_model=list[WalletBalanceOut])
async def get_wallet_balances(
    wallet_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    balance_service: Annotated[BalanceService, Depends(get_balance_service)],
) -> list[WalletBalanceOut]:
    balances = await balance_service.get_wallet_balances(wallet_id, user_id)
    return [WalletBalanceOut(currency_id=currency_id, balance=balance) for currency_id, balance in balances]
