from typing import Protocol
from uuid import UUID


class WalletUsageChecker(Protocol):
    async def references_wallet(self, wallet_id: UUID) -> bool: ...
