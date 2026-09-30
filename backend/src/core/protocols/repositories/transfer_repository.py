from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from core.entities import Transfer


class TransferRepository(Protocol):
    async def add(self, transfer: Transfer) -> Transfer: ...

    async def get_by_id(self, transfer_id: UUID, workspace_id: UUID) -> Transfer | None: ...

    async def list(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Transfer]: ...

    async def count(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int: ...

    async def update(
        self,
        transfer_id: UUID,
        workspace_id: UUID,
        *,
        from_wallet_id: UUID,
        to_wallet_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime,
        now: datetime,
    ) -> Transfer | None: ...

    async def delete(self, transfer_id: UUID, workspace_id: UUID) -> bool: ...

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID) -> dict[UUID, Decimal]: ...
