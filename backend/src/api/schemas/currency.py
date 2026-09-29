from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CurrencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    decimal_places: int
