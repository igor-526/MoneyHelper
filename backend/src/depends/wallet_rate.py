from typing import Annotated

from fastapi import Depends

from core.protocols import TransactionRepository, WalletRepository
from core.services.wallet_rate import WalletRateService
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository


def get_wallet_rate_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
) -> WalletRateService:
    return WalletRateService(transactions, wallets)
