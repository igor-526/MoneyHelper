from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import Clock, CurrencyRepository, IdGenerator, TransferRepository, WalletRepository
from core.services.transfer import TransferService
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator
from depends.wallet import get_wallet_repository
from repositories.transfer import TransferRepository as SqlTransferRepository
from utils.database import get_session


def get_transfer_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> TransferRepository:
    return SqlTransferRepository(session)


def get_transfer_service(
    transfers: Annotated[TransferRepository, Depends(get_transfer_repository)],
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> TransferService:
    return TransferService(transfers, wallets, currencies, clock, ids)
