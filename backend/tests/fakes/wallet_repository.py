from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from core.entities import Wallet


class InMemoryWalletRepository:
    def __init__(self) -> None:
        self._wallets: dict[UUID, Wallet] = {}

    async def add(self, wallet: Wallet) -> Wallet:
        self._wallets[wallet.id] = wallet
        return wallet

    async def get_by_id(self, wallet_id: UUID, workspace_id: UUID) -> Wallet | None:
        wallet = self._wallets.get(wallet_id)
        return wallet if wallet is not None and wallet.workspace_id == workspace_id else None

    async def list(self, workspace_id: UUID, *, limit: int, offset: int) -> list[Wallet]:
        items = sorted(
            (wallet for wallet in self._wallets.values() if wallet.workspace_id == workspace_id),
            key=lambda wallet: (wallet.created_at, wallet.id),
        )
        return items[offset : offset + limit]

    async def count(self, workspace_id: UUID) -> int:
        return sum(1 for wallet in self._wallets.values() if wallet.workspace_id == workspace_id)

    async def update(
        self, wallet_id: UUID, workspace_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID], now: datetime
    ) -> Wallet | None:
        wallet = self._wallets.get(wallet_id)
        if wallet is None or wallet.workspace_id != workspace_id:
            return None
        updated = wallet.model_copy(
            update={"name": name, "icon": icon, "currency_ids": tuple(currency_ids), "updated_at": now}
        )
        self._wallets[wallet_id] = updated
        return updated

    async def delete(self, wallet_id: UUID, workspace_id: UUID) -> bool:
        wallet = self._wallets.get(wallet_id)
        if wallet is None or wallet.workspace_id != workspace_id:
            return False
        del self._wallets[wallet_id]
        return True
