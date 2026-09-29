from typing import Annotated

from fastapi import Depends

from core.protocols import TransactionRepository, TransferRepository, WalletRepository
from core.services.balance import BalanceService
from depends.transaction import get_transaction_repository
from depends.transfer import get_transfer_repository
from depends.wallet import get_wallet_repository


def get_balance_service(
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    transfers: Annotated[TransferRepository, Depends(get_transfer_repository)],
) -> BalanceService:
    return BalanceService(wallets, [transactions, transfers])
