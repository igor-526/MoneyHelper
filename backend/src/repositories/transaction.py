from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Row, case, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import CategoryType, LegRecord, TopupLegRecord, Transaction, TransactionLeg
from models import categories, currencies, transaction_legs, transactions


def _map_row(row: Row[Any], legs: tuple[TransactionLeg, ...]) -> Transaction:
    return Transaction(
        id=row.id,
        workspace_id=row.workspace_id,
        wallet_id=row.wallet_id,
        category_id=row.category_id,
        legs=legs,
        occurred_at=row.occurred_at,
        comment=row.comment,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, transaction: Transaction) -> Transaction:
        await self._session.execute(
            insert(transactions).values(
                id=transaction.id,
                workspace_id=transaction.workspace_id,
                wallet_id=transaction.wallet_id,
                category_id=transaction.category_id,
                occurred_at=transaction.occurred_at,
                comment=transaction.comment,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
        )
        await self._insert_legs(transaction.id, transaction.legs)
        return await self.get_by_id(transaction.id, transaction.workspace_id) or transaction

    async def get_by_id(self, transaction_id: UUID, workspace_id: UUID) -> Transaction | None:
        row = (
            await self._session.execute(
                select(transactions).where(
                    transactions.c.id == transaction_id, transactions.c.workspace_id == workspace_id
                )
            )
        ).first()
        if row is None:
            return None
        legs = await self._load_legs(transaction_id)
        return _map_row(row, legs)

    # `list_legs_for_analytics`/`list_topup_legs_for_rates` объявлены раньше `list`/`count` в теле класса:
    # имя `list` внутри тела класса начинает ссылаться на одноимённый метод сразу после его определения
    # (Python вычисляет аннотации `def` эагерно в пространстве имён класса), поэтому бare-аннотация
    # `-> list[LegRecord]` ниже перестала бы резолвиться к встроенному generic-типу, если бы шла после
    # `async def list(...)` (тот же приём уже применён в `tests/fakes/transaction_repository.py`).
    async def list_legs_for_analytics(
        self,
        workspace_id: UUID,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        wallet_id: UUID | None,
        category_id: UUID | None,
        currency_id: UUID | None,
        type: CategoryType | None,
    ) -> list[LegRecord]:
        query = (
            select(
                transactions.c.wallet_id,
                transactions.c.category_id,
                transaction_legs.c.currency_id,
                transaction_legs.c.amount,
                transactions.c.occurred_at,
                categories.c.type,
            )
            .select_from(
                transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id).join(
                    categories, categories.c.id == transactions.c.category_id
                )
            )
            .where(transactions.c.workspace_id == workspace_id)
        )
        if date_from is not None:
            query = query.where(transactions.c.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(transactions.c.occurred_at <= date_to)
        if wallet_id is not None:
            query = query.where(transactions.c.wallet_id == wallet_id)
        if category_id is not None:
            query = query.where(transactions.c.category_id == category_id)
        if currency_id is not None:
            query = query.where(transaction_legs.c.currency_id == currency_id)
        if type is not None:
            query = query.where(categories.c.type == type)
        rows = await self._session.execute(query)
        return [
            LegRecord(
                wallet_id=row.wallet_id,
                category_id=row.category_id,
                currency_id=row.currency_id,
                amount=row.amount,
                category_type=row.type,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]

    async def list_topup_legs_for_rates(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[TopupLegRecord]:
        query = (
            select(transaction_legs.c.transaction_id, transaction_legs.c.currency_id, transaction_legs.c.amount)
            .select_from(
                transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id).join(
                    categories, categories.c.id == transactions.c.category_id
                )
            )
            .where(transactions.c.workspace_id == workspace_id, categories.c.type == CategoryType.INCOME)
        )
        query = self._apply_filters(
            query, wallet_id=wallet_id, category_id=None, type=None, date_from=date_from, date_to=date_to
        )
        rows = await self._session.execute(query)
        return [
            TopupLegRecord(transaction_id=row.transaction_id, currency_id=row.currency_id, amount=row.amount)
            for row in rows
        ]

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
        query = self._filtered_query(
            workspace_id, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        rows = (
            await self._session.execute(
                query.order_by(transactions.c.occurred_at.desc(), transactions.c.id.desc()).limit(limit).offset(offset)
            )
        ).all()
        if not rows:
            return []
        legs_by_transaction = await self._load_legs_map([row.id for row in rows])
        return [_map_row(row, legs_by_transaction.get(row.id, ())) for row in rows]

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
        joined: Any = transactions
        if type is not None:
            joined = joined.join(categories, transactions.c.category_id == categories.c.id)
        query = select(func.count()).select_from(joined).where(transactions.c.workspace_id == workspace_id)
        query = self._apply_filters(
            query, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        return (await self._session.execute(query)).scalar_one()

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
        result = await self._session.execute(
            sa_update(transactions)
            .where(transactions.c.id == transaction_id, transactions.c.workspace_id == workspace_id)
            .values(
                wallet_id=wallet_id, category_id=category_id, occurred_at=occurred_at, comment=comment, updated_at=now
            )
            .returning(transactions.c.id)
        )
        if result.first() is None:
            return None
        await self._session.execute(
            sa_delete(transaction_legs).where(transaction_legs.c.transaction_id == transaction_id)
        )
        await self._insert_legs(transaction_id, legs)
        return await self.get_by_id(transaction_id, workspace_id)

    async def delete(self, transaction_id: UUID, workspace_id: UUID) -> bool:
        result = await self._session.execute(
            sa_delete(transactions)
            .where(transactions.c.id == transaction_id, transactions.c.workspace_id == workspace_id)
            .returning(transactions.c.id)
        )
        return result.first() is not None

    async def references_wallet(self, wallet_id: UUID) -> bool:
        return (
            await self._session.execute(
                select(transactions.c.id).where(transactions.c.wallet_id == wallet_id).limit(1)
            )
        ).first() is not None

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal:
        signed_amount = case(
            (categories.c.type == CategoryType.INCOME, transaction_legs.c.amount), else_=-transaction_legs.c.amount
        )
        query = (
            select(func.coalesce(func.sum(signed_amount), 0))
            .select_from(
                transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id).join(
                    categories, categories.c.id == transactions.c.category_id
                )
            )
            .where(
                transactions.c.wallet_id == wallet_id,
                transactions.c.workspace_id == workspace_id,
                transaction_legs.c.currency_id == currency_id,
            )
        )
        return (await self._session.execute(query)).scalar_one()

    async def _insert_legs(self, transaction_id: UUID, legs: Sequence[TransactionLeg]) -> None:
        if not legs:
            return
        await self._session.execute(
            insert(transaction_legs),
            [{"transaction_id": transaction_id, "currency_id": leg.currency_id, "amount": leg.amount} for leg in legs],
        )

    async def _load_legs(self, transaction_id: UUID) -> tuple[TransactionLeg, ...]:
        return (await self._load_legs_map([transaction_id])).get(transaction_id, ())

    async def _load_legs_map(self, transaction_ids: Sequence[UUID]) -> dict[UUID, tuple[TransactionLeg, ...]]:
        if not transaction_ids:
            return {}
        rows = await self._session.execute(
            select(transaction_legs.c.transaction_id, transaction_legs.c.currency_id, transaction_legs.c.amount)
            .select_from(transaction_legs.join(currencies, transaction_legs.c.currency_id == currencies.c.id))
            .where(transaction_legs.c.transaction_id.in_(transaction_ids))
            .order_by(transaction_legs.c.transaction_id, currencies.c.code)
        )
        grouped: dict[UUID, list[TransactionLeg]] = defaultdict(list)
        for row in rows:
            grouped[row.transaction_id].append(TransactionLeg(currency_id=row.currency_id, amount=row.amount))
        return {transaction_id: tuple(legs) for transaction_id, legs in grouped.items()}

    def _filtered_query(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Any:
        joined: Any = transactions
        if type is not None:
            joined = joined.join(categories, transactions.c.category_id == categories.c.id)
        query = select(transactions).select_from(joined).where(transactions.c.workspace_id == workspace_id)
        return self._apply_filters(
            query, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )

    def _apply_filters(
        self,
        query: Any,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Any:
        if wallet_id is not None:
            query = query.where(transactions.c.wallet_id == wallet_id)
        if category_id is not None:
            query = query.where(transactions.c.category_id == category_id)
        if type is not None:
            query = query.where(categories.c.type == type)
        if date_from is not None:
            query = query.where(transactions.c.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(transactions.c.occurred_at <= date_to)
        return query
