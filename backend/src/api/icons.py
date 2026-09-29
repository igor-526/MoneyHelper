from fastapi import APIRouter

from core.icons import list_icon_names

router = APIRouter(prefix="/api/icons", tags=["Icons"])


@router.get("", response_model=list[str])
async def list_icons() -> list[str]:
    return list_icon_names()
