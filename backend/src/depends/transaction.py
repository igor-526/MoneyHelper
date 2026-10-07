from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    OperationClock,
    TransactionRepository,
    WalletRepository,
)
from core.services.transaction import TransactionService
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator, get_operation_clock
from depends.wallet import get_wallet_repository
from repositories.transaction import TransactionRepository as SqlTransactionRepository
from utils.database import get_session


def get_transaction_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> TransactionRepository:
    return SqlTransactionRepository(session)


def get_transaction_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    operation_clock: Annotated[OperationClock, Depends(get_operation_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> TransactionService:
    return TransactionService(transactions, wallets, categories, currencies, clock, operation_clock, ids)
