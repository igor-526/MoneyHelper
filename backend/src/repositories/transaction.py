from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Row, case, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import CategoryType, Transaction
from models import categories, transaction_legs, transactions

_JOINED = transactions.join(transaction_legs, transactions.c.id == transaction_legs.c.transaction_id)


def _map_row(row: Row[Any]) -> Transaction:
    return Transaction(
        id=row.id,
        user_id=row.user_id,
        wallet_id=row.wallet_id,
        category_id=row.category_id,
        currency_id=row.currency_id,
        amount=row.amount,
        occurred_at=row.occurred_at,
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
                user_id=transaction.user_id,
                wallet_id=transaction.wallet_id,
                category_id=transaction.category_id,
                occurred_at=transaction.occurred_at,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
        )
        await self._session.execute(
            insert(transaction_legs).values(
                transaction_id=transaction.id, currency_id=transaction.currency_id, amount=transaction.amount
            )
        )
        return transaction

    async def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        row = (
            await self._session.execute(
                select(transactions, transaction_legs.c.currency_id, transaction_legs.c.amount)
                .select_from(_JOINED)
                .where(transactions.c.id == transaction_id, transactions.c.user_id == user_id)
            )
        ).first()
        return _map_row(row) if row is not None else None

    async def list(
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
    ) -> list[Transaction]:
        query = self._filtered_query(
            user_id, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        rows = (
            await self._session.execute(
                query.order_by(transactions.c.occurred_at.desc(), transactions.c.id.desc()).limit(limit).offset(offset)
            )
        ).all()
        return [_map_row(row) for row in rows]

    async def count(
        self,
        user_id: UUID,
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
        query = select(func.count()).select_from(joined).where(transactions.c.user_id == user_id)
        query = self._apply_filters(
            query, wallet_id=wallet_id, category_id=category_id, type=type, date_from=date_from, date_to=date_to
        )
        return (await self._session.execute(query)).scalar_one()

    async def update(
        self,
        transaction_id: UUID,
        user_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime,
        now: datetime,
    ) -> Transaction | None:
        result = await self._session.execute(
            sa_update(transactions)
            .where(transactions.c.id == transaction_id, transactions.c.user_id == user_id)
            .values(wallet_id=wallet_id, category_id=category_id, occurred_at=occurred_at, updated_at=now)
            .returning(transactions.c.id)
        )
        if result.first() is None:
            return None
        await self._session.execute(
            sa_delete(transaction_legs).where(transaction_legs.c.transaction_id == transaction_id)
        )
        await self._session.execute(
            insert(transaction_legs).values(transaction_id=transaction_id, currency_id=currency_id, amount=amount)
        )
        return await self.get_by_id(transaction_id, user_id)

    async def delete(self, transaction_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            sa_delete(transactions)
            .where(transactions.c.id == transaction_id, transactions.c.user_id == user_id)
            .returning(transactions.c.id)
        )
        return result.first() is not None

    async def balances(self, wallet_id: UUID, user_id: UUID) -> dict[UUID, Decimal]:
        signed_amount = case(
            (categories.c.type == CategoryType.INCOME, transaction_legs.c.amount), else_=-transaction_legs.c.amount
        )
        query = (
            select(transaction_legs.c.currency_id, func.sum(signed_amount).label("balance"))
            .select_from(
                transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id).join(
                    categories, categories.c.id == transactions.c.category_id
                )
            )
            .where(transactions.c.wallet_id == wallet_id, transactions.c.user_id == user_id)
            .group_by(transaction_legs.c.currency_id)
        )
        rows = await self._session.execute(query)
        return {row.currency_id: row.balance for row in rows}

    def _filtered_query(
        self,
        user_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Any:
        joined = _JOINED
        if type is not None:
            joined = joined.join(categories, transactions.c.category_id == categories.c.id)
        query = (
            select(transactions, transaction_legs.c.currency_id, transaction_legs.c.amount)
            .select_from(joined)
            .where(transactions.c.user_id == user_id)
        )
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
