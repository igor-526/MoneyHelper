from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schemas import Money


class WalletBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency_id: UUID
    balance: Money
