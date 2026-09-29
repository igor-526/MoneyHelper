from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.transfer import TransferCreate, TransferListParams, TransferOut, TransferUpdate
from core.schemas import Page
from core.services.transfer import TransferService
from depends.auth import get_current_user
from depends.transfer import get_transfer_service

router = APIRouter(prefix="/api/transfers", tags=["Transfers"])


@router.post("", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: TransferCreate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferOut:
    transfer = await transfer_service.create_transfer(
        user_id,
        from_wallet_id=body.from_wallet_id,
        to_wallet_id=body.to_wallet_id,
        currency_id=body.currency_id,
        amount=body.amount,
        occurred_at=body.occurred_at,
    )
    return TransferOut.model_validate(transfer)


@router.get("", response_model=Page[TransferOut])
async def list_transfers(
    params: Annotated[TransferListParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> Page[TransferOut]:
    items, total = await transfer_service.list_transfers(
        user_id,
        wallet_id=params.wallet_id,
        date_from=params.date_from,
        date_to=params.date_to,
        limit=params.limit,
        offset=params.offset,
    )
    return Page[TransferOut](
        items=[TransferOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{transfer_id}", response_model=TransferOut)
async def get_transfer(
    transfer_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferOut:
    transfer = await transfer_service.get_transfer(transfer_id, user_id)
    return TransferOut.model_validate(transfer)


@router.put("/{transfer_id}", response_model=TransferOut)
async def update_transfer(
    transfer_id: UUID,
    body: TransferUpdate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferOut:
    transfer = await transfer_service.update_transfer(
        transfer_id,
        user_id,
        from_wallet_id=body.from_wallet_id,
        to_wallet_id=body.to_wallet_id,
        currency_id=body.currency_id,
        amount=body.amount,
        occurred_at=body.occurred_at,
    )
    return TransferOut.model_validate(transfer)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transfer(
    transfer_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> None:
    await transfer_service.delete_transfer(transfer_id, user_id)
