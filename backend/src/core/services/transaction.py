from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import CategoryType, Transaction
from core.exceptions import ClientError, NotFoundError
from core.protocols import (
    CategoryRepository,
    Clock,
    CurrencyRepository,
    IdGenerator,
    TransactionRepository,
    WalletRepository,
)

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
        user_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transaction:
        await self._validate_transaction_input(
            user_id, wallet_id=wallet_id, category_id=category_id, currency_id=currency_id, amount=amount
        )
        now = self._clock.now()
        transaction = Transaction(
            id=self._ids.new(),
            user_id=user_id,
            wallet_id=wallet_id,
            category_id=category_id,
            currency_id=currency_id,
            amount=amount,
            occurred_at=occurred_at if occurred_at is not None else now,
            created_at=now,
        )
        return await self._transactions.add(transaction)

    async def get_transaction(self, transaction_id: UUID, user_id: UUID) -> Transaction:
        transaction = await self._transactions.get_by_id(transaction_id, user_id)
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def list_transactions(
        self,
        user_id: UUID,
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
            user_id,
            wallet_id=wallet_id,
            category_id=category_id,
            type=type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        total = await self._transactions.count(
            user_id, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        return items, total

    async def update_transaction(
        self,
        transaction_id: UUID,
        user_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime | None,
    ) -> Transaction:
        await self._validate_transaction_input(
            user_id, wallet_id=wallet_id, category_id=category_id, currency_id=currency_id, amount=amount
        )
        now = self._clock.now()
        transaction = await self._transactions.update(
            transaction_id,
            user_id,
            wallet_id=wallet_id,
            category_id=category_id,
            currency_id=currency_id,
            amount=amount,
            occurred_at=occurred_at if occurred_at is not None else now,
            now=now,
        )
        if transaction is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return transaction

    async def delete_transaction(self, transaction_id: UUID, user_id: UUID) -> None:
        deleted = await self._transactions.delete(transaction_id, user_id)
        if not deleted:
            raise NotFoundError(NOT_FOUND_MESSAGE)

    async def get_wallet_balances(self, wallet_id: UUID, user_id: UUID) -> list[tuple[UUID, Decimal]]:
        wallet = await self._wallets.get_by_id(wallet_id, user_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        balances = await self._transactions.balances(wallet_id, user_id)
        return [(currency_id, balances.get(currency_id, Decimal("0"))) for currency_id in wallet.currency_ids]

    async def _validate_transaction_input(
        self, user_id: UUID, *, wallet_id: UUID, category_id: UUID, currency_id: UUID, amount: Decimal
    ) -> None:
        wallet = await self._wallets.get_by_id(wallet_id, user_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        category = await self._categories.get_by_id(category_id, user_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        if currency_id not in wallet.currency_ids:
            raise ClientError("Валюта операции не входит в набор валют кошелька")
        currency = await self._currencies.get_by_id(currency_id)
        if currency is None:
            raise ClientError("Неизвестная валюта операции")
        exponent = amount.as_tuple().exponent
        if isinstance(exponent, int) and exponent < 0 and -exponent > currency.decimal_places:
            raise ClientError(
                f"Сумма содержит больше {currency.decimal_places} знаков после запятой, "
                f"допустимых для валюты {currency.code}"
            )
