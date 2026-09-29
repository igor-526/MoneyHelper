from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, insert, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Wallet
from models import currencies, wallet_currencies, wallets


def _map_row(row: Row[Any], currency_ids: tuple[UUID, ...]) -> Wallet:
    return Wallet(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        icon=row.icon,
        currency_ids=currency_ids,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, wallet: Wallet) -> Wallet:
        await self._session.execute(
            insert(wallets).values(
                id=wallet.id,
                user_id=wallet.user_id,
                name=wallet.name,
                icon=wallet.icon,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at,
            )
        )
        await self._insert_currency_ids(wallet.id, wallet.currency_ids)
        return await self.get_by_id(wallet.id, wallet.user_id) or wallet

    async def get_by_id(self, wallet_id: UUID, user_id: UUID) -> Wallet | None:
        row = (
            await self._session.execute(select(wallets).where(wallets.c.id == wallet_id, wallets.c.user_id == user_id))
        ).first()
        if row is None:
            return None
        currency_ids = await self._load_currency_ids(wallet_id)
        return _map_row(row, currency_ids)

    async def list(self, user_id: UUID, *, limit: int, offset: int) -> list[Wallet]:
        rows = (
            await self._session.execute(
                select(wallets)
                .where(wallets.c.user_id == user_id)
                .order_by(wallets.c.created_at, wallets.c.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        if not rows:
            return []
        currency_ids_by_wallet = await self._load_currency_ids_map([row.id for row in rows])
        return [_map_row(row, currency_ids_by_wallet.get(row.id, ())) for row in rows]

    async def count(self, user_id: UUID) -> int:
        return (
            await self._session.execute(select(func.count()).select_from(wallets).where(wallets.c.user_id == user_id))
        ).scalar_one()

    async def update(
        self, wallet_id: UUID, user_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID], now: datetime
    ) -> Wallet | None:
        result = await self._session.execute(
            sa_update(wallets)
            .where(wallets.c.id == wallet_id, wallets.c.user_id == user_id)
            .values(name=name, icon=icon, updated_at=now)
            .returning(wallets)
        )
        row = result.first()
        if row is None:
            return None
        await self._session.execute(sa_delete(wallet_currencies).where(wallet_currencies.c.wallet_id == wallet_id))
        await self._insert_currency_ids(wallet_id, currency_ids)
        return _map_row(row, tuple(await self._load_currency_ids(wallet_id)))

    async def delete(self, wallet_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            sa_delete(wallets).where(wallets.c.id == wallet_id, wallets.c.user_id == user_id).returning(wallets.c.id)
        )
        return result.first() is not None

    async def _insert_currency_ids(self, wallet_id: UUID, currency_ids: Sequence[UUID]) -> None:
        if not currency_ids:
            return
        await self._session.execute(
            insert(wallet_currencies),
            [{"wallet_id": wallet_id, "currency_id": currency_id} for currency_id in currency_ids],
        )

    async def _load_currency_ids(self, wallet_id: UUID) -> tuple[UUID, ...]:
        return (await self._load_currency_ids_map([wallet_id])).get(wallet_id, ())

    async def _load_currency_ids_map(self, wallet_ids: Sequence[UUID]) -> dict[UUID, tuple[UUID, ...]]:
        if not wallet_ids:
            return {}
        rows = await self._session.execute(
            select(wallet_currencies.c.wallet_id, wallet_currencies.c.currency_id)
            .select_from(wallet_currencies.join(currencies, wallet_currencies.c.currency_id == currencies.c.id))
            .where(wallet_currencies.c.wallet_id.in_(wallet_ids))
            .order_by(wallet_currencies.c.wallet_id, currencies.c.code)
        )
        grouped: dict[UUID, list[UUID]] = defaultdict(list)
        for row in rows:
            grouped[row.wallet_id].append(row.currency_id)
        return {wallet_id: tuple(ids) for wallet_id, ids in grouped.items()}
