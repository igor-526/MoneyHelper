from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import Transfer


class InMemoryTransferRepository:
    def __init__(self) -> None:
        self._transfers: dict[UUID, Transfer] = {}

    def _filter(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[Transfer]:
        result = []
        for transfer in self._transfers.values():
            if transfer.workspace_id != workspace_id:
                continue
            if wallet_id is not None and wallet_id not in (transfer.from_wallet_id, transfer.to_wallet_id):
                continue
            if date_from is not None and transfer.occurred_at < date_from:
                continue
            if date_to is not None and transfer.occurred_at > date_to:
                continue
            result.append(transfer)
        return result

    async def add(self, transfer: Transfer) -> Transfer:
        self._transfers[transfer.id] = transfer
        return transfer

    async def get_by_id(self, transfer_id: UUID, workspace_id: UUID) -> Transfer | None:
        transfer = self._transfers.get(transfer_id)
        return transfer if transfer is not None and transfer.workspace_id == workspace_id else None

    async def list(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Transfer]:
        items = sorted(
            self._filter(workspace_id, wallet_id=wallet_id, date_from=date_from, date_to=date_to),
            key=lambda transfer: (transfer.occurred_at, transfer.id),
            reverse=True,
        )
        return items[offset : offset + limit]

    async def count(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return len(self._filter(workspace_id, wallet_id=wallet_id, date_from=date_from, date_to=date_to))

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
    ) -> Transfer | None:
        transfer = self._transfers.get(transfer_id)
        if transfer is None or transfer.workspace_id != workspace_id:
            return None
        updated = transfer.model_copy(
            update={
                "from_wallet_id": from_wallet_id,
                "to_wallet_id": to_wallet_id,
                "currency_id": currency_id,
                "amount": amount,
                "occurred_at": occurred_at,
                "updated_at": now,
            }
        )
        self._transfers[transfer_id] = updated
        return updated

    async def delete(self, transfer_id: UUID, workspace_id: UUID) -> bool:
        transfer = self._transfers.get(transfer_id)
        if transfer is None or transfer.workspace_id != workspace_id:
            return False
        del self._transfers[transfer_id]
        return True

    async def references_wallet(self, wallet_id: UUID) -> bool:
        """Не часть протокола — вспомогательный метод для тестов, симулирующих `ON DELETE RESTRICT`
        `transfers.from_wallet_id`/`transfers.to_wallet_id` на fake-репозиториях кошельков."""
        return any(
            wallet_id in (transfer.from_wallet_id, transfer.to_wallet_id) for transfer in self._transfers.values()
        )

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID) -> dict[UUID, Decimal]:
        totals: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for transfer in self._transfers.values():
            if transfer.workspace_id != workspace_id:
                continue
            if transfer.to_wallet_id == wallet_id:
                totals[transfer.currency_id] += transfer.amount
            elif transfer.from_wallet_id == wallet_id:
                totals[transfer.currency_id] -= transfer.amount
        return dict(totals)
