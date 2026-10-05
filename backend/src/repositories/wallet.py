from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Wallet
from core.exceptions import ConflictError
from models import wallets

DELETE_CONFLICT_MESSAGE = "Кошелёк нельзя удалить: есть операции"


def _map_row(row: Row[Any]) -> Wallet:
    return Wallet(
        id=row.id,
        workspace_id=row.workspace_id,
        name=row.name,
        icon=row.icon,
        currency_id=row.currency_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, wallet: Wallet) -> Wallet:
        result = await self._session.execute(
            insert(wallets)
            .values(
                id=wallet.id,
                workspace_id=wallet.workspace_id,
                name=wallet.name,
                icon=wallet.icon,
                currency_id=wallet.currency_id,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at,
            )
            .returning(wallets)
        )
        return _map_row(result.one())

    async def get_by_id(self, wallet_id: UUID, workspace_id: UUID) -> Wallet | None:
        row = (
            await self._session.execute(
                select(wallets).where(wallets.c.id == wallet_id, wallets.c.workspace_id == workspace_id)
            )
        ).first()
        return _map_row(row) if row is not None else None

    async def list(self, workspace_id: UUID, *, limit: int, offset: int) -> list[Wallet]:
        rows = (
            await self._session.execute(
                select(wallets)
                .where(wallets.c.workspace_id == workspace_id)
                .order_by(wallets.c.created_at, wallets.c.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [_map_row(row) for row in rows]

    async def count(self, workspace_id: UUID) -> int:
        return (
            await self._session.execute(
                select(func.count()).select_from(wallets).where(wallets.c.workspace_id == workspace_id)
            )
        ).scalar_one()

    async def get_currency_id_by_wallet(self, workspace_id: UUID) -> dict[UUID, UUID]:
        rows = await self._session.execute(
            select(wallets.c.id, wallets.c.currency_id).where(wallets.c.workspace_id == workspace_id)
        )
        return {row.id: row.currency_id for row in rows}

    async def update(
        self, wallet_id: UUID, workspace_id: UUID, *, name: str, icon: str, currency_id: UUID, now: datetime
    ) -> Wallet | None:
        result = await self._session.execute(
            sa_update(wallets)
            .where(wallets.c.id == wallet_id, wallets.c.workspace_id == workspace_id)
            .values(name=name, icon=icon, currency_id=currency_id, updated_at=now)
            .returning(wallets)
        )
        row = result.first()
        return _map_row(row) if row is not None else None

    async def delete(self, wallet_id: UUID, workspace_id: UUID) -> bool:
        try:
            result = await self._session.execute(
                sa_delete(wallets)
                .where(wallets.c.id == wallet_id, wallets.c.workspace_id == workspace_id)
                .returning(wallets.c.id)
            )
        except IntegrityError as exc:
            raise ConflictError(DELETE_CONFLICT_MESSAGE) from exc
        return result.first() is not None
