from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schemas import Money, PageParams


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_wallet_id: UUID
    to_wallet_id: UUID
    amount: Money = Field(gt=0)
    occurred_at: datetime | None = None


TransferUpdate = TransferCreate


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_wallet_id: UUID
    to_wallet_id: UUID
    amount: Money
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime | None


class TransferListParams(PageParams):
    """`PageParams` с фильтрами списка переводов (см. `TransactionListParams`)."""

    wallet_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
