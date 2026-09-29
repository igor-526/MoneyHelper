from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import CurrencyRepository
from core.services.currency import CurrencyService
from repositories.currency import CurrencyRepository as SqlCurrencyRepository
from utils.database import get_session


def get_currency_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> CurrencyRepository:
    return SqlCurrencyRepository(session)


def get_currency_service(
    repository: Annotated[CurrencyRepository, Depends(get_currency_repository)],
) -> CurrencyService:
    return CurrencyService(repository)
