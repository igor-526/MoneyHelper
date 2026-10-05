from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.schemas.transaction import COMMENT_MAX_LENGTH, TransactionLegOut, normalize_comment_text
from core.schemas import Money, PageParams


class TopupLegIn(BaseModel):
    currency_id: UUID
    amount: Money = Field(gt=0)


class TopupCreate(BaseModel):
    wallet_id: UUID
    category_id: UUID
    legs: list[TopupLegIn]
    occurred_at: datetime | None = None
    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        return normalize_comment_text(value)


TopupUpdate = TopupCreate


class TopupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wallet_id: UUID
    category_id: UUID
    legs: list[TransactionLegOut]
    occurred_at: datetime
    comment: str | None
    created_at: datetime
    updated_at: datetime | None


class TopupListParams(PageParams):
    """`PageParams` с фильтрами списка пополнений (фильтры внутри модели — см. `TransactionListParams`)."""

    wallet_id: UUID | None = None
    category_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
