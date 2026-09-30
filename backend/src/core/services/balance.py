from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from core.exceptions import NotFoundError
from core.protocols import BalanceContributor, WalletRepository

WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"


class BalanceService:
    def __init__(self, wallets: WalletRepository, contributors: Sequence[BalanceContributor]) -> None:
        self._wallets = wallets
        self._contributors = contributors

    async def get_wallet_balances(self, wallet_id: UUID, workspace_id: UUID) -> list[tuple[UUID, Decimal]]:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        totals: dict[UUID, Decimal] = {}
        for contributor in self._contributors:
            for currency_id, delta in (await contributor.balance_delta(wallet_id, workspace_id)).items():
                totals[currency_id] = totals.get(currency_id, Decimal("0")) + delta
        return [(currency_id, totals.get(currency_id, Decimal("0"))) for currency_id in wallet.currency_ids]
