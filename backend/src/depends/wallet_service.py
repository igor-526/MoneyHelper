from typing import Annotated

from fastapi import Depends

from core.protocols import (
    Clock,
    CurrencyRepository,
    IdGenerator,
    TransactionRepository,
    WalletRepository,
)
from core.services.wallet import WalletService
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository


def get_wallet_service(
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> WalletService:
    return WalletService(wallets, currencies, [transactions], clock, ids)
