from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.schemas.workspace import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate
from core.schemas import Page, PageParams
from core.services.workspace import WorkspaceService
from depends.auth import get_current_user
from depends.workspace import get_workspace_service

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceOut:
    workspace = await workspace_service.create_workspace(user_id, name=body.name)
    return WorkspaceOut.model_validate(workspace)


@router.get("", response_model=Page[WorkspaceOut])
async def list_workspaces(
    params: Annotated[PageParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> Page[WorkspaceOut]:
    items, total = await workspace_service.list_workspaces(user_id, limit=params.limit, offset=params.offset)
    return Page[WorkspaceOut](
        items=[WorkspaceOut.model_validate(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceOut:
    workspace = await workspace_service.get_workspace(workspace_id, user_id)
    return WorkspaceOut.model_validate(workspace)


@router.put("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceOut:
    workspace = await workspace_service.update_workspace(workspace_id, user_id, name=body.name)
    return WorkspaceOut.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    await workspace_service.delete_workspace(workspace_id, user_id)
