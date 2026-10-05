from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.topup import TopupCreate, TopupListParams, TopupOut, TopupUpdate
from core.entities import TransactionLeg
from core.schemas import Page
from core.services.topup import TopupService
from depends.topup import get_topup_service
from depends.workspace import require_workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}/topups", tags=["Topups"])


@router.post("", response_model=TopupOut, status_code=status.HTTP_201_CREATED)
async def create_topup(
    body: TopupCreate,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    topup_service: Annotated[TopupService, Depends(get_topup_service)],
) -> TopupOut:
    topup = await topup_service.create_topup(
        workspace_id,
        wallet_id=body.wallet_id,
        category_id=body.category_id,
        legs=[TransactionLeg(currency_id=leg.currency_id, amount=leg.amount) for leg in body.legs],
        occurred_at=body.occurred_at,
        comment=body.comment,
    )
    return TopupOut.model_validate(topup)


@router.get("", response_model=Page[TopupOut])
async def list_topups(
    params: Annotated[TopupListParams, Query()],
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    topup_service: Annotated[TopupService, Depends(get_topup_service)],
) -> Page[TopupOut]:
    items, total = await topup_service.list_topups(
        workspace_id,
        wallet_id=params.wallet_id,
        category_id=params.category_id,
        date_from=params.date_from,
        date_to=params.date_to,
        limit=params.limit,
        offset=params.offset,
    )
    return Page[TopupOut](
        items=[TopupOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{topup_id}", response_model=TopupOut)
async def get_topup(
    topup_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    topup_service: Annotated[TopupService, Depends(get_topup_service)],
) -> TopupOut:
    topup = await topup_service.get_topup(topup_id, workspace_id)
    return TopupOut.model_validate(topup)


@router.put("/{topup_id}", response_model=TopupOut)
async def update_topup(
    topup_id: UUID,
    body: TopupUpdate,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    topup_service: Annotated[TopupService, Depends(get_topup_service)],
) -> TopupOut:
    topup = await topup_service.update_topup(
        topup_id,
        workspace_id,
        wallet_id=body.wallet_id,
        category_id=body.category_id,
        legs=[TransactionLeg(currency_id=leg.currency_id, amount=leg.amount) for leg in body.legs],
        occurred_at=body.occurred_at,
        comment=body.comment,
    )
    return TopupOut.model_validate(topup)


@router.delete("/{topup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topup(
    topup_id: UUID,
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    topup_service: Annotated[TopupService, Depends(get_topup_service)],
) -> None:
    await topup_service.delete_topup(topup_id, workspace_id)
