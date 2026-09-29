from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schemas import IconName


class WalletCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: IconName
    currency_ids: list[UUID]

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name не может быть пустым")
        return stripped

    @field_validator("currency_ids")
    @classmethod
    def validate_currency_ids(cls, value: list[UUID]) -> list[UUID]:
        if not value:
            raise ValueError("currency_ids не может быть пустым списком")
        if len(set(value)) != len(value):
            raise ValueError("currency_ids не должен содержать дубликаты")
        return value


WalletUpdate = WalletCreate


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    icon: str
    currency_ids: list[UUID]
    created_at: datetime
    updated_at: datetime | None
