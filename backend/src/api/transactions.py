from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.transaction import (
    TopupCreate,
    TransactionCreate,
    TransactionListParams,
    TransactionOut,
    TransactionUpdate,
)
from core.entities import TransactionLeg
from core.schemas import Page
from core.services.transaction import TransactionService
from depends.transaction import get_transaction_service
from depends.workspace import require_workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}/transactions", tags=["Transactions"])


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionOut:
    transaction = await transaction_service.create_transaction(
        workspace_id,
        wallet_id=body.wallet_id,
        category_id=body.category_id,
        currency_id=body.currency_id,
        amount=body.amount,
        occurred_at=body.occurred_at,
    )
    return TransactionOut.model_validate(transaction)


# Статический маршрут `/topups` объявлен раньше параметризованных `/{transaction_id}` ниже: Starlette
# сопоставляет маршруты в порядке регистрации, и при обратном порядке `"topups"` мог бы быть ошибочно
# разобран как `transaction_id` (см. design.md, раздел 10).
@router.post("/topups", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_topup(
    body: TopupCreate,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionOut:
    transaction = await transaction_service.create_topup(
        workspace_id,
        wallet_id=body.wallet_id,
        category_id=body.category_id,
        legs=[TransactionLeg(currency_id=leg.currency_id, amount=leg.amount) for leg in body.legs],
        occurred_at=body.occurred_at,
    )
    return TransactionOut.model_validate(transaction)


@router.get("", response_model=Page[TransactionOut])
async def list_transactions(
    params: Annotated[TransactionListParams, Query()],
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> Page[TransactionOut]:
    items, total = await transaction_service.list_transactions(
        workspace_id,
        wallet_id=params.wallet_id,
        category_id=params.category_id,
        type=params.type,
        date_from=params.date_from,
        date_to=params.date_to,
        limit=params.limit,
        offset=params.offset,
    )
    return Page[TransactionOut](
        items=[TransactionOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionOut:
    transaction = await transaction_service.get_transaction(transaction_id, workspace_id)
    return TransactionOut.model_validate(transaction)


@router.put("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: UUID,
    body: TransactionUpdate,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionOut:
    transaction = await transaction_service.update_transaction(
        transaction_id,
        workspace_id,
        wallet_id=body.wallet_id,
        category_id=body.category_id,
        currency_id=body.currency_id,
        amount=body.amount,
        occurred_at=body.occurred_at,
    )
    return TransactionOut.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> None:
    await transaction_service.delete_transaction(transaction_id, workspace_id)
