from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities import CategoryType, LegRecord, TopupLegRecord, Transaction, TransactionLeg
from tests.fakes.category_repository import InMemoryCategoryRepository


class InMemoryTransactionRepository:
    """`type` операции у настоящего репозитория вычисляется JOIN'ом с `categories.type` (см. design.md),
    поэтому fake-репозиторий получает ссылку на `InMemoryCategoryRepository`, чтобы читать тип категории так же."""

    def __init__(self, categories: InMemoryCategoryRepository) -> None:
        self._categories = categories
        self._transactions: dict[UUID, Transaction] = {}

    async def _filter(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[Transaction]:
        # Метод объявлен раньше `list`/`count` в теле класса: имя `list` внутри тела класса начинает ссылаться
        # на одноимённый метод сразу после его определения, поэтому аннотация `-> list[Transaction]` ниже
        # перестала бы резолвиться к встроенному generic-типу, если бы шла после `async def list(...)`.
        result = []
        for transaction in self._transactions.values():
            if transaction.workspace_id != workspace_id:
                continue
            if wallet_id is not None and transaction.wallet_id != wallet_id:
                continue
            if category_id is not None and transaction.category_id != category_id:
                continue
            if type is not None:
                category = await self._categories.get_by_id(transaction.category_id, workspace_id)
                if category is None or category.type != type:
                    continue
            if date_from is not None and transaction.occurred_at < date_from:
                continue
            if date_to is not None and transaction.occurred_at > date_to:
                continue
            result.append(transaction)
        return result

    async def add(self, transaction: Transaction) -> Transaction:
        self._transactions[transaction.id] = transaction
        return transaction

    async def get_by_id(self, transaction_id: UUID, workspace_id: UUID) -> Transaction | None:
        transaction = self._transactions.get(transaction_id)
        return transaction if transaction is not None and transaction.workspace_id == workspace_id else None

    # Объявлены раньше `list`/`count` — та же причина, что и у `_filter` выше.
    async def list_legs_for_analytics(
        self,
        workspace_id: UUID,
        *,
        date_from: datetime,
        date_to: datetime,
        wallet_id: UUID | None,
        category_id: UUID | None,
        currency_id: UUID | None,
        type: CategoryType | None,
    ) -> list[LegRecord]:
        records = []
        for transaction in self._transactions.values():
            if transaction.workspace_id != workspace_id:
                continue
            if transaction.occurred_at < date_from or transaction.occurred_at > date_to:
                continue
            if wallet_id is not None and transaction.wallet_id != wallet_id:
                continue
            if category_id is not None and transaction.category_id != category_id:
                continue
            category = await self._categories.get_by_id(transaction.category_id, workspace_id)
            if category is None:
                continue
            if type is not None and category.type != type:
                continue
            for leg in transaction.legs:
                if currency_id is not None and leg.currency_id != currency_id:
                    continue
                records.append(
                    LegRecord(
                        wallet_id=transaction.wallet_id,
                        category_id=transaction.category_id,
                        currency_id=leg.currency_id,
                        amount=leg.amount,
                        category_type=category.type,
                    )
                )
        return records

    async def list_topup_legs_for_rates(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[TopupLegRecord]:
        records = []
        for transaction in await self._filter(
            workspace_id,
            wallet_id=wallet_id,
            category_id=None,
            type=CategoryType.INCOME,
            date_from=date_from,
            date_to=date_to,
        ):
            for leg in transaction.legs:
                records.append(
                    TopupLegRecord(transaction_id=transaction.id, currency_id=leg.currency_id, amount=leg.amount)
                )
        return records

    async def list(
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
    ) -> list[Transaction]:
        items = sorted(
            await self._filter(
                workspace_id,
                wallet_id=wallet_id,
                category_id=category_id,
                type=type,
                date_from=date_from,
                date_to=date_to,
            ),
            key=lambda transaction: (transaction.occurred_at, transaction.id),
            reverse=True,
        )
        return items[offset : offset + limit]

    async def count(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return len(
            await self._filter(
                workspace_id,
                wallet_id=wallet_id,
                category_id=category_id,
                type=type,
                date_from=date_from,
                date_to=date_to,
            )
        )

    async def update(
        self,
        transaction_id: UUID,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: Sequence[TransactionLeg],
        occurred_at: datetime,
        comment: str | None,
        now: datetime,
    ) -> Transaction | None:
        transaction = self._transactions.get(transaction_id)
        if transaction is None or transaction.workspace_id != workspace_id:
            return None
        updated = transaction.model_copy(
            update={
                "wallet_id": wallet_id,
                "category_id": category_id,
                "legs": tuple(legs),
                "occurred_at": occurred_at,
                "comment": comment,
                "updated_at": now,
            }
        )
        self._transactions[transaction_id] = updated
        return updated

    async def delete(self, transaction_id: UUID, workspace_id: UUID) -> bool:
        transaction = self._transactions.get(transaction_id)
        if transaction is None or transaction.workspace_id != workspace_id:
            return False
        del self._transactions[transaction_id]
        return True

    async def references_wallet(self, wallet_id: UUID) -> bool:
        return any(transaction.wallet_id == wallet_id for transaction in self._transactions.values())

    async def references_category(self, category_id: UUID) -> bool:
        """Аналогично `references_wallet`, но для `ON DELETE RESTRICT` `transactions.category_id`."""
        return any(transaction.category_id == category_id for transaction in self._transactions.values())

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal:
        total = Decimal("0")
        for transaction in self._transactions.values():
            if transaction.workspace_id != workspace_id or transaction.wallet_id != wallet_id:
                continue
            category = await self._categories.get_by_id(transaction.category_id, workspace_id)
            sign = 1 if category is not None and category.type == CategoryType.INCOME else -1
            for leg in transaction.legs:
                if leg.currency_id == currency_id:
                    total += sign * leg.amount
        return total
