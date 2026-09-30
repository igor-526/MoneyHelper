from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.entities import Wallet


class WalletRepository(Protocol):
    async def add(self, wallet: Wallet) -> Wallet: ...

    async def get_by_id(self, wallet_id: UUID, workspace_id: UUID) -> Wallet | None: ...

    async def list(self, workspace_id: UUID, *, limit: int, offset: int) -> list[Wallet]: ...

    async def count(self, workspace_id: UUID) -> int: ...

    async def update(
        self, wallet_id: UUID, workspace_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID], now: datetime
    ) -> Wallet | None: ...

    async def delete(self, wallet_id: UUID, workspace_id: UUID) -> bool: ...
