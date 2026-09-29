from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from core.entities import CategoryType, Transaction


class TransactionRepository(Protocol):
    async def add(self, transaction: Transaction) -> Transaction: ...

    async def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None: ...

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
    ) -> list[Transaction]: ...

    async def count(
        self,
        user_id: UUID,
        *,
        wallet_id: UUID | None,
        category_id: UUID | None,
        type: CategoryType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int: ...

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
    ) -> Transaction | None: ...

    async def delete(self, transaction_id: UUID, user_id: UUID) -> bool: ...

    async def balances(self, wallet_id: UUID, user_id: UUID) -> dict[UUID, Decimal]: ...
