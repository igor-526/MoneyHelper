from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schemas import Rate


class WalletRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_currency_id: UUID
    wallet_currency_id: UUID
    rate: Rate | None
