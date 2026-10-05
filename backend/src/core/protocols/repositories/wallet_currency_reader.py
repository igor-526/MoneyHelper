from typing import Protocol
from uuid import UUID


class WalletCurrencyReader(Protocol):
    async def get_currency_id_by_wallet(self, workspace_id: UUID) -> dict[UUID, UUID]: ...
