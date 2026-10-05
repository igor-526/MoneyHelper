from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from core.entities import CategoryType, LegRecord, TopupLegRecord, Transaction, TransactionLeg


class TransactionRepository(Protocol):
    async def add(self, transaction: Transaction) -> Transaction: ...

    async def get_by_id(self, transaction_id: UUID, workspace_id: UUID) -> Transaction | None: ...

    # Объявлены раньше `list`/`count`: имя `list` внутри тела класса начинает ссылаться на одноимённый метод
    # сразу после его определения (см. тот же приём и комментарий в `repositories/transaction.py` и
    # `tests/fakes/transaction_repository.py`), поэтому bare-аннотация `-> list[LegRecord]` ниже перестала бы
    # резолвиться к встроенному generic-типу, если бы шла после `async def list(...)`.
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
    ) -> list[LegRecord]: ...

    async def list_topup_legs_for_rates(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[TopupLegRecord]: ...

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
    ) -> list[Transaction]: ...

    async def count(
        self,
        workspace_id: UUID,
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
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: Sequence[TransactionLeg],
        occurred_at: datetime,
        comment: str | None,
        now: datetime,
    ) -> Transaction | None: ...

    async def delete(self, transaction_id: UUID, workspace_id: UUID) -> bool: ...

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal: ...

    async def references_wallet(self, wallet_id: UUID) -> bool: ...
