from typing import Annotated

from fastapi import Depends

from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    TransactionRepository,
    WalletRepository,
    WorkspaceCurrencyReader,
)
from core.services.topup import TopupService
from core.services.topup_legs import CrossCurrencyTopupLegs, SameCurrencyTopupLegs
from depends.category import get_category_repository
from depends.currency import get_currency_repository
from depends.providers import get_clock, get_id_generator
from depends.transaction import get_transaction_repository
from depends.wallet import get_wallet_repository
from depends.workspace import get_workspace_repository


def get_topup_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
    workspaces: Annotated[WorkspaceCurrencyReader, Depends(get_workspace_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> TopupService:
    return TopupService(
        transactions,
        wallets,
        categories,
        currencies,
        workspaces,
        (SameCurrencyTopupLegs(), CrossCurrencyTopupLegs()),
        clock,
        ids,
    )
