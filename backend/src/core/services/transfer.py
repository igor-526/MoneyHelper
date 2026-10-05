from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import Transfer, Wallet
from core.exceptions import ClientError, NotFoundError
from core.protocols import Clock, CurrencyRepository, IdGenerator, TransferRepository, WalletRepository
from core.services.money_validation import ensure_amount_precision

NOT_FOUND_MESSAGE = "Перевод не найден"
WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
SAME_CURRENCY_MESSAGE = "Перевод возможен только между кошельками одной валюты"


class TransferService:
    def __init__(
        self,
        transfers: TransferRepository,
        wallets: WalletRepository,
        currencies: CurrencyRepository,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._transfers = transfers
        self._wallets = wallets
        self._currencies = currencies
        self._clock = clock
        self._ids = ids

    async def create_transfer(
        self,
        workspace_id: UUID,
        *,
        from_wallet_id: UUID,
        to_wallet_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transfer:
        await self._validate_transfer_input(
            workspace_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
        )
        now = self._clock.now()
        transfer = Transfer(
            id=self._ids.new(),
            workspace_id=workspace_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            occurred_at=occurred_at if occurred_at is not None else now,
            created_at=now,
        )
        return await self._transfers.add(transfer)

    async def get_transfer(self, transfer_id: UUID, workspace_id: UUID) -> Transfer:
        transfer = await self._transfers.get_by_id(transfer_id, workspace_id)
        if transfer is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transfer

    async def list_transfers(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Transfer], int]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClientError("date_from не может быть позже date_to")
        items = await self._transfers.list(
            workspace_id, wallet_id=wallet_id, date_from=date_from, date_to=date_to, limit=limit, offset=offset
        )
        total = await self._transfers.count(workspace_id, wallet_id=wallet_id, date_from=date_from, date_to=date_to)
        return items, total

    async def update_transfer(
        self,
        transfer_id: UUID,
        workspace_id: UUID,
        *,
        from_wallet_id: UUID,
        to_wallet_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transfer:
        await self._validate_transfer_input(
            workspace_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
        )
        now = self._clock.now()
        transfer = await self._transfers.update(
            transfer_id,
            workspace_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            occurred_at=occurred_at if occurred_at is not None else now,
            now=now,
        )
        if transfer is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transfer

    async def delete_transfer(self, transfer_id: UUID, workspace_id: UUID) -> None:
        deleted = await self._transfers.delete(transfer_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _validate_transfer_input(
        self,
        workspace_id: UUID,
        *,
        from_wallet_id: UUID,
        to_wallet_id: UUID,
        amount: Decimal,
    ) -> None:
        if from_wallet_id == to_wallet_id:
            raise ClientError("Кошелёк отправителя и получателя не может совпадать")
        from_wallet = await self._get_owned_wallet(from_wallet_id, workspace_id)
        to_wallet = await self._get_owned_wallet(to_wallet_id, workspace_id)
        if from_wallet.currency_id != to_wallet.currency_id:
            raise ClientError(SAME_CURRENCY_MESSAGE)
        if amount <= 0:
            raise ClientError("Сумма должна быть положительной")
        currency = await self._currencies.get_by_id(from_wallet.currency_id)
        if currency is None:
            raise ClientError("Неизвестная валюта перевода")
        ensure_amount_precision(amount, currency)

    async def _get_owned_wallet(self, wallet_id: UUID, workspace_id: UUID) -> Wallet:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        return wallet
