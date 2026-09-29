from datetime import timedelta
from typing import Annotated

from fastapi import Depends

from core.protocols import Clock
from depends.providers import get_clock
from settings import settings
from utils.jwt_tokens import JwtTokenService


def get_token_service(clock: Annotated[Clock, Depends(get_clock)]) -> JwtTokenService:
    """Реализует и TokenIssuer, и TokenVerifier; FastAPI кэширует зависимость в рамках запроса, поэтому
    оба протокола резолвятся в один и тот же экземпляр."""
    return JwtTokenService(
        secret=settings.jwt_secret,
        clock=clock,
        access_ttl=timedelta(minutes=settings.access_token_ttl_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_ttl_days),
    )
