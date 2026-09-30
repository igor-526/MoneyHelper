from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from core.exceptions import ClientError, NotFoundError
from core.protocols import TransactionRepository, WalletRepository
from core.schemas.rate import RATE_DECIMAL_PLACES
from core.services.rate_averaging import average_rates

WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
UNKNOWN_TARGET_CURRENCY_MESSAGE = "target_currency_id должен быть одной из валют кошелька"


@dataclass(frozen=True)
class WalletRates:
    target_currency_id: UUID
    rates: dict[UUID, Decimal]
    unrated_currency_ids: list[UUID]


def _round(rate: Decimal) -> Decimal:
    return rate.quantize(Decimal(1).scaleb(-RATE_DECIMAL_PLACES), rounding=ROUND_HALF_UP)


class WalletRateService:
    def __init__(self, transactions: TransactionRepository, wallets: WalletRepository) -> None:
        self._transactions = transactions
        self._wallets = wallets

    async def get_wallet_rates(self, wallet_id: UUID, workspace_id: UUID, *, target_currency_id: UUID) -> WalletRates:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        if target_currency_id not in wallet.currency_ids:
            raise ClientError(UNKNOWN_TARGET_CURRENCY_MESSAGE)

        source_ids = {currency_id for currency_id in wallet.currency_ids if currency_id != target_currency_id}
        if not source_ids:
            return WalletRates(target_currency_id=target_currency_id, rates={}, unrated_currency_ids=[])

        topup_legs = await self._transactions.list_topup_legs_for_wallet_rates(workspace_id, wallet_id)
        rates = {
            currency_id: _round(rate)
            for currency_id, rate in average_rates(topup_legs, target_currency_id, source_ids).items()
        }
        unrated_currency_ids = sorted(source_ids - rates.keys(), key=str)
        return WalletRates(
            target_currency_id=target_currency_id, rates=rates, unrated_currency_ids=unrated_currency_ids
        )
