from decimal import Decimal
from typing import Protocol
from uuid import UUID


class BalanceContributor(Protocol):
    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal: ...
