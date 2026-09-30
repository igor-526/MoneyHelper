from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import CategoryType, Currency, Transaction, TransactionLeg, Wallet
from core.exceptions import ClientError, NotFoundError
from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    TransactionRepository,
    WalletRepository,
)
from core.services.money_validation import ensure_amount_precision

NOT_FOUND_MESSAGE = "Операция не найдена"
WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
CATEGORY_NOT_FOUND_MESSAGE = "Категория не найдена"


class TransactionService:
    def __init__(
        self,
        transactions: TransactionRepository,
        wallets: WalletRepository,
        categories: CategoryRepository,
        currencies: CurrencyRepository,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._transactions = transactions
        self._wallets = wallets
        self._categories = categories
        self._currencies = currencies
        self._clock = clock
        self._ids = ids

    async def create_transaction(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transaction:
        await self._validate_transaction_input(
            workspace_id, wallet_id=wallet_id, category_id=category_id, currency_id=currency_id, amount=amount
        )
        now = self._clock.now()
        transaction = Transaction(
            id=self._ids.new(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=currency_id, amount=amount),),
            occurred_at=occurred_at if occurred_at is not None else now,
            created_at=now,
        )
        return await self._transactions.add(transaction)

    async def create_topup(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: Sequence[TransactionLeg],
        occurred_at: datetime | None,
    ) -> Transaction:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        category = await self._categories.get_by_id(category_id, workspace_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        if category.type is not CategoryType.INCOME:
            raise ClientError("Пополнение возможно только с категорией дохода")
        await self._ensure_legs_match_wallet_currencies(wallet, legs)
        for leg in legs:
            await self._validate_leg_amount(leg.currency_id, leg.amount)
        now = self._clock.now()
        transaction = Transaction(
            id=self._ids.new(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=tuple(legs),
            occurred_at=occurred_at if occurred_at is not None else now,
            created_at=now,
        )
        return await self._transactions.add(transaction)

    async def get_transaction(self, transaction_id: UUID, workspace_id: UUID) -> Transaction:
        transaction = await self._transactions.get_by_id(transaction_id, workspace_id)
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def list_transactions(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Transaction], int]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClientError("date_from не может быть позже date_to")
        items = await self._transactions.list(
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            type=type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        total = await self._transactions.count(
            workspace_id, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        return items, total

    async def update_transaction(
        self,
        transaction_id: UUID,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transaction:
        await self._validate_transaction_input(
            workspace_id, wallet_id=wallet_id, category_id=category_id, currency_id=currency_id, amount=amount
        )
        now = self._clock.now()
        transaction = await self._transactions.update(
            transaction_id,
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=currency_id, amount=amount),),
            occurred_at=occurred_at if occurred_at is not None else now,
            now=now,
        )
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def delete_transaction(self, transaction_id: UUID, workspace_id: UUID) -> None:
        deleted = await self._transactions.delete(transaction_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _validate_transaction_input(
        self, workspace_id: UUID, *, wallet_id: UUID, category_id: UUID, currency_id: UUID, amount: Decimal
    ) -> Wallet:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        category = await self._categories.get_by_id(category_id, workspace_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        if currency_id not in wallet.currency_ids:
            raise ClientError("Валюта операции не входит в набор валют кошелька")
        await self._validate_leg_amount(currency_id, amount)
        return wallet

    async def _validate_leg_amount(self, currency_id: UUID, amount: Decimal) -> Currency:
        if amount <= 0:
            raise ClientError("Сумма должна быть положительной")
        currency = await self._currencies.get_by_id(currency_id)
        if currency is None:
            raise ClientError("Неизвестная валюта операции")
        ensure_amount_precision(amount, currency)
        return currency

    async def _ensure_legs_match_wallet_currencies(self, wallet: Wallet, legs: Sequence[TransactionLeg]) -> None:
        leg_currency_ids = [leg.currency_id for leg in legs]
        if len(leg_currency_ids) != len(set(leg_currency_ids)):
            raise ClientError("Валюта в пополнении указана более одного раза")
        wallet_currency_ids = set(wallet.currency_ids)
        leg_currency_id_set = set(leg_currency_ids)
        if leg_currency_id_set == wallet_currency_ids:
            return
        missing = wallet_currency_ids - leg_currency_id_set
        extra = leg_currency_id_set - wallet_currency_ids
        parts = []
        if missing:
            parts.append(f"отсутствуют ноги для валют: {await self._currency_codes_text(missing)}")
        if extra:
            parts.append(f"лишние валюты в ногах: {await self._currency_codes_text(extra)}")
        raise ClientError("; ".join(parts))

    async def _currency_codes_text(self, currency_ids: set[UUID]) -> str:
        codes = []
        for currency_id in currency_ids:
            currency = await self._currencies.get_by_id(currency_id)
            codes.append(currency.code if currency is not None else str(currency_id))
        return ", ".join(sorted(codes))
