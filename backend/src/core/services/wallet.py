from collections.abc import Sequence
from uuid import UUID

from core.entities import Wallet
from core.exceptions import ClientError, ConflictError, NotFoundError
from core.protocols import Clock, CurrencyRepository, IdGenerator, WalletRepository, WalletUsageChecker

NOT_FOUND_MESSAGE = "Кошелёк не найден"
CURRENCY_CHANGE_CONFLICT_MESSAGE = "Валюту кошелька нельзя изменить: есть операции"


class WalletService:
    def __init__(
        self,
        wallets: WalletRepository,
        currencies: CurrencyRepository,
        usage_checkers: Sequence[WalletUsageChecker],
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._wallets = wallets
        self._currencies = currencies
        self._usage_checkers = usage_checkers
        self._clock = clock
        self._ids = ids

    async def create_wallet(self, workspace_id: UUID, *, name: str, icon: str, currency_id: UUID) -> Wallet:
        await self._ensure_currency_exists(currency_id)
        wallet = Wallet(
            id=self._ids.new(),
            workspace_id=workspace_id,
            name=name,
            icon=icon,
            currency_id=currency_id,
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
        self, wallet_id: UUID, workspace_id: UUID, *, name: str, icon: str, currency_id: UUID
    ) -> Wallet:
        current = await self.get_wallet(wallet_id, workspace_id)
        if currency_id != current.currency_id:
            await self._ensure_currency_exists(currency_id)
            await self._ensure_wallet_unused(wallet_id)
        wallet = await self._wallets.update(
            wallet_id, workspace_id, name=name, icon=icon, currency_id=currency_id, now=self._clock.now()
        )
        if wallet is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return wallet

    async def delete_wallet(self, wallet_id: UUID, workspace_id: UUID) -> None:
        deleted = await self._wallets.delete(wallet_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _ensure_currency_exists(self, currency_id: UUID) -> None:
        if await self._currencies.missing_ids([currency_id]):
            raise ClientError(f"Неизвестный currency_id: {currency_id}")

    async def _ensure_wallet_unused(self, wallet_id: UUID) -> None:
        for checker in self._usage_checkers:
            if await checker.references_wallet(wallet_id):
                raise ConflictError(CURRENCY_CHANGE_CONFLICT_MESSAGE)
