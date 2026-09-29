from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.wallet import WalletCreate, WalletOut, WalletUpdate
from core.schemas import Page, PageParams
from core.services.wallet import WalletService
from depends.auth import get_current_user
from depends.wallet import get_wallet_service

router = APIRouter(prefix="/api/wallets", tags=["Wallets"])


@router.post("", response_model=WalletOut, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    body: WalletCreate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletOut:
    wallet = await wallet_service.create_wallet(
        user_id, name=body.name, icon=body.icon, currency_ids=body.currency_ids
    )
    return WalletOut.model_validate(wallet)


@router.get("", response_model=Page[WalletOut])
async def list_wallets(
    params: Annotated[PageParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> Page[WalletOut]:
    items, total = await wallet_service.list_wallets(user_id, limit=params.limit, offset=params.offset)
    return Page[WalletOut](
        items=[WalletOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{wallet_id}", response_model=WalletOut)
async def get_wallet(
    wallet_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletOut:
    wallet = await wallet_service.get_wallet(wallet_id, user_id)
    return WalletOut.model_validate(wallet)


@router.put("/{wallet_id}", response_model=WalletOut)
async def update_wallet(
    wallet_id: UUID,
    body: WalletUpdate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletOut:
    wallet = await wallet_service.update_wallet(
        wallet_id, user_id, name=body.name, icon=body.icon, currency_ids=body.currency_ids
    )
    return WalletOut.model_validate(wallet)


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet(
    wallet_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> None:
    await wallet_service.delete_wallet(wallet_id, user_id)
