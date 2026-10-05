from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import WalletRepository
from repositories.wallet import WalletRepository as SqlWalletRepository
from utils.database import get_session


def get_wallet_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> WalletRepository:
    return SqlWalletRepository(session)
