from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Row, case, func, insert, or_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Transfer
from models import transfers


def _map_row(row: Row[Any]) -> Transfer:
    return Transfer(
        id=row.id,
        workspace_id=row.workspace_id,
        from_wallet_id=row.from_wallet_id,
        to_wallet_id=row.to_wallet_id,
        amount=row.amount,
        occurred_at=row.occurred_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, transfer: Transfer) -> Transfer:
        await self._session.execute(
            insert(transfers).values(
                id=transfer.id,
                workspace_id=transfer.workspace_id,
                from_wallet_id=transfer.from_wallet_id,
                to_wallet_id=transfer.to_wallet_id,
                amount=transfer.amount,
                occurred_at=transfer.occurred_at,
                created_at=transfer.created_at,
                updated_at=transfer.updated_at,
            )
        )
        return transfer

    async def get_by_id(self, transfer_id: UUID, workspace_id: UUID) -> Transfer | None:
        row = (
            await self._session.execute(
                select(transfers).where(transfers.c.id == transfer_id, transfers.c.workspace_id == workspace_id)
            )
        ).first()
        return _map_row(row) if row is not None else None

    async def list(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Transfer]:
        query = self._filtered_query(workspace_id, wallet_id=wallet_id, date_from=date_from, date_to=date_to)
        rows = (
            await self._session.execute(
                query.order_by(transfers.c.occurred_at.desc(), transfers.c.id.desc()).limit(limit).offset(offset)
            )
        ).all()
        return [_map_row(row) for row in rows]

    async def count(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        query = select(func.count()).select_from(transfers).where(transfers.c.workspace_id == workspace_id)
        query = self._apply_filters(query, wallet_id=wallet_id, date_from=date_from, date_to=date_to)
        return (await self._session.execute(query)).scalar_one()

    async def update(
        self,
        transfer_id: UUID,
        workspace_id: UUID,
        *,
        from_wallet_id: UUID,
        to_wallet_id: UUID,
        amount: Decimal,
        occurred_at: datetime,
        now: datetime,
    ) -> Transfer | None:
        result = await self._session.execute(
            sa_update(transfers)
            .where(transfers.c.id == transfer_id, transfers.c.workspace_id == workspace_id)
            .values(
                from_wallet_id=from_wallet_id,
                to_wallet_id=to_wallet_id,
                amount=amount,
                occurred_at=occurred_at,
                updated_at=now,
            )
            .returning(transfers)
        )
        row = result.first()
        return _map_row(row) if row is not None else None

    async def delete(self, transfer_id: UUID, workspace_id: UUID) -> bool:
        result = await self._session.execute(
            sa_delete(transfers)
            .where(transfers.c.id == transfer_id, transfers.c.workspace_id == workspace_id)
            .returning(transfers.c.id)
        )
        return result.first() is not None

    async def references_wallet(self, wallet_id: UUID) -> bool:
        query = (
            select(transfers.c.id)
            .where(or_(transfers.c.to_wallet_id == wallet_id, transfers.c.from_wallet_id == wallet_id))
            .limit(1)
        )
        return (await self._session.execute(query)).first() is not None

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal:
        signed_amount = case((transfers.c.to_wallet_id == wallet_id, transfers.c.amount), else_=-transfers.c.amount)
        query = select(func.coalesce(func.sum(signed_amount), 0)).where(
            transfers.c.workspace_id == workspace_id,
            or_(transfers.c.to_wallet_id == wallet_id, transfers.c.from_wallet_id == wallet_id),
        )
        return (await self._session.execute(query)).scalar_one()

    def _filtered_query(
        self, workspace_id: UUID, *, wallet_id: UUID | None, date_from: datetime | None, date_to: datetime | None
    ) -> Any:
        query = select(transfers).where(transfers.c.workspace_id == workspace_id)
        return self._apply_filters(query, wallet_id=wallet_id, date_from=date_from, date_to=date_to)

    def _apply_filters(
        self, query: Any, *, wallet_id: UUID | None, date_from: datetime | None, date_to: datetime | None
    ) -> Any:
        if wallet_id is not None:
            query = query.where(or_(transfers.c.from_wallet_id == wallet_id, transfers.c.to_wallet_id == wallet_id))
        if date_from is not None:
            query = query.where(transfers.c.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(transfers.c.occurred_at <= date_to)
        return query
