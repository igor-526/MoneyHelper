from collections.abc import Sequence
from uuid import UUID

from core.entities import Wallet
from core.exceptions import ClientError, NotFoundError
from core.protocols import Clock, CurrencyRepository, IdGenerator, WalletRepository

NOT_FOUND_MESSAGE = "Кошелёк не найден"


class WalletService:
    def __init__(
        self, wallets: WalletRepository, currencies: CurrencyRepository, clock: Clock, ids: IdGenerator
    ) -> None:
        self._wallets = wallets
        self._currencies = currencies
        self._clock = clock
        self._ids = ids

    async def create_wallet(self, workspace_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID]) -> Wallet:
        await self._ensure_currencies_exist(currency_ids)
        wallet = Wallet(
            id=self._ids.new(),
            workspace_id=workspace_id,
            name=name,
            icon=icon,
            currency_ids=tuple(currency_ids),
            created_at=self._clock.now(),
        )
        return await self._wallets.add(wallet)

    async def get_wallet(self, wallet_id: UUID, workspace_id: UUID) -> Wallet:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return wallet

    async def list_wallets(self, workspace_id: UUID, *, limit: int, offset: int) -> tuple[list[Wallet], int]:
        items = await self._wallets.list(workspace_id, limit=limit, offset=offset)
        total = await self._wallets.count(workspace_id)
        return items, total

    async def update_wallet(
        self, wallet_id: UUID, workspace_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID]
    ) -> Wallet:
        await self._ensure_currencies_exist(currency_ids)
        wallet = await self._wallets.update(
            wallet_id, workspace_id, name=name, icon=icon, currency_ids=currency_ids, now=self._clock.now()
        )
        if wallet is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return wallet

    async def delete_wallet(self, wallet_id: UUID, workspace_id: UUID) -> None:
        deleted = await self._wallets.delete(wallet_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _ensure_currencies_exist(self, currency_ids: Sequence[UUID]) -> None:
        missing = await self._currencies.missing_ids(currency_ids)
        if missing:
            ids_text = ", ".join(str(currency_id) for currency_id in sorted(missing))
            raise ClientError(f"Неизвестные currency_id: {ids_text}")
