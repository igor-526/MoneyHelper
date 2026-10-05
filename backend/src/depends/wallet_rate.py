from typing import Annotated

from fastapi import Depends

from core.protocols import TransactionRepository, WalletRepository, WorkspaceCurrencyReader
from core.services.wallet_rate import WalletRateService
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository


def get_wallet_rate_service(
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    workspaces: Annotated[WorkspaceCurrencyReader, Depends(get_workspace_repository)],
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> WalletRateService:
    return WalletRateService(wallets, workspaces, transactions)
