from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from core.exceptions import NotFoundError
from core.protocols import TransactionRepository, WalletRepository, WorkspaceCurrencyReader
from core.schemas.rate import RATE_DECIMAL_PLACES
from core.services.rate_averaging import average_rates

WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
RATE_QUANTUM = Decimal(1).scaleb(-RATE_DECIMAL_PLACES)


@dataclass(frozen=True)
class WalletRate:
    workspace_currency_id: UUID
    wallet_currency_id: UUID
    rate: Decimal | None


class WalletRateService:
    def __init__(
        self,
        wallets: WalletRepository,
        workspaces: WorkspaceCurrencyReader,
        transactions: TransactionRepository,
    ) -> None:
        self._wallets = wallets
        self._workspaces = workspaces
        self._transactions = transactions

    async def get_wallet_rate(self, wallet_id: UUID, workspace_id: UUID) -> WalletRate:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        workspace_currency_id = await self._workspaces.get_currency_id(workspace_id)
        if wallet is None or workspace_currency_id is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        if wallet.currency_id == workspace_currency_id:
            return WalletRate(workspace_currency_id, wallet.currency_id, Decimal(1).quantize(RATE_QUANTUM))
        topup_legs = await self._transactions.list_topup_legs_for_rates(workspace_id, wallet_id=wallet_id)
        rate = average_rates(topup_legs, workspace_currency_id, {wallet.currency_id}).get(wallet.currency_id)
        if rate is not None:
            rate = rate.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
        return WalletRate(workspace_currency_id, wallet.currency_id, rate)
