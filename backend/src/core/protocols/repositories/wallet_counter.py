from typing import Protocol
from uuid import UUID


class WalletCounter(Protocol):
    async def count(self, workspace_id: UUID) -> int: ...
