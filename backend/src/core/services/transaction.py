from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import CategoryType, Transaction, TransactionLeg, Wallet
from core.exceptions import ClientError, NotFoundError
from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    OperationClock,
    TransactionRepository,
    WalletRepository,
)
from core.services.money_validation import validate_leg_amount
from core.services.transaction_kind import get_of_type

NOT_FOUND_MESSAGE = "Операция не найдена"
WALLET_NOT_FOUND_MESSAGE = "Кошелёк не найден"
CATEGORY_NOT_FOUND_MESSAGE = "Категория не найдена"
INCOME_REJECTED_MESSAGE = "Доход создаётся пополнением кошелька, а не операцией"


class TransactionService:
    def __init__(
        self,
        transactions: TransactionRepository,
        wallets: WalletRepository,
        categories: CategoryRepository,
        currencies: CurrencyRepository,
        clock: Clock,
        operation_clock: OperationClock,
        ids: IdGenerator,
    ) -> None:
        self._transactions = transactions
        self._wallets = wallets
        self._categories = categories
        self._currencies = currencies
        self._clock = clock
        self._operation_clock = operation_clock
        self._ids = ids

    async def create_transaction(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
        comment: str | None = None,
    ) -> Transaction:
        wallet = await self._validate_transaction_input(
            workspace_id, wallet_id=wallet_id, category_id=category_id, amount=amount
        )
        now = self._clock.now()
        transaction = Transaction(
            id=self._ids.new(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=wallet.currency_id, amount=amount),),
            occurred_at=occurred_at if occurred_at is not None else self._operation_clock.now(),
            comment=comment,
            created_at=now,
        )
        return await self._transactions.add(transaction)

    async def get_transaction(self, transaction_id: UUID, workspace_id: UUID) -> Transaction:
        transaction = await get_of_type(
            self._transactions, self._categories, transaction_id, workspace_id, CategoryType.EXPENSE
        )
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def list_transactions(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
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
            type=CategoryType.EXPENSE,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        total = await self._transactions.count(
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            type=CategoryType.EXPENSE,
            date_from=date_from,
            date_to=date_to,
        )
        return items, total

    async def update_transaction(
        self,
        transaction_id: UUID,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
        comment: str | None = None,
    ) -> Transaction:
        await self.get_transaction(transaction_id, workspace_id)
        wallet = await self._validate_transaction_input(
            workspace_id, wallet_id=wallet_id, category_id=category_id, amount=amount
        )
        now = self._clock.now()
        transaction = await self._transactions.update(
            transaction_id,
            workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=wallet.currency_id, amount=amount),),
            occurred_at=occurred_at if occurred_at is not None else self._operation_clock.now(),
            comment=comment,
            now=now,
        )
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def delete_transaction(self, transaction_id: UUID, workspace_id: UUID) -> None:
        await self.get_transaction(transaction_id, workspace_id)
        deleted = await self._transactions.delete(transaction_id, workspace_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def _validate_transaction_input(
        self, workspace_id: UUID, *, wallet_id: UUID, category_id: UUID, amount: Decimal
    ) -> Wallet:
        wallet = await self._wallets.get_by_id(wallet_id, workspace_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        category = await self._categories.get_by_id(category_id, workspace_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        if category.type is not CategoryType.EXPENSE:
            raise ClientError(INCOME_REJECTED_MESSAGE)
        await validate_leg_amount(self._currencies, wallet.currency_id, amount)
        return wallet
