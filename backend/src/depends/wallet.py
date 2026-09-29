from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import Clock, CurrencyRepository, IdGenerator, WalletRepository
from core.services.wallet import WalletService
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator
from repositories.wallet import WalletRepository as SqlWalletRepository
from utils.database import get_session


def get_wallet_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> WalletRepository:
    return SqlWalletRepository(session)


def get_wallet_service(
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> WalletService:
    return WalletService(wallets, currencies, clock, ids)
