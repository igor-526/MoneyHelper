from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schemas import Rate


class CurrencyRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency_id: UUID
    rate: Rate


class WalletRatesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_currency_id: UUID
    rates: list[CurrencyRateOut]
    unrated_currency_ids: list[UUID]
