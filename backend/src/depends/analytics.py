from typing import Annotated

from fastapi import Depends

from core.protocols import CurrencyRepository, TransactionRepository
from core.services.analytics import AnalyticsService
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository


def get_analytics_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
) -> AnalyticsService:
    return AnalyticsService(transactions, currencies)
