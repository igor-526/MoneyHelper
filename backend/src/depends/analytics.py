from typing import Annotated

from fastapi import Depends

from core.protocols import CurrencyRepository, TransactionRepository, WalletCurrencyReader, WorkspaceCurrencyReader
from core.services.analytics import AnalyticsService
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository


def get_analytics_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    wallets: Annotated[WalletCurrencyReader, Depends(get_wallet_repository)],
    workspaces: Annotated[WorkspaceCurrencyReader, Depends(get_workspace_repository)],
) -> AnalyticsService:
    return AnalyticsService(transactions, currencies, wallets, workspaces)
