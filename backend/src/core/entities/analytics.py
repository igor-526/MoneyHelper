from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from core.entities.category import CategoryType


class LegRecord(BaseModel):
    wallet_id: UUID
    category_id: UUID
    currency_id: UUID
    amount: Decimal
    category_type: CategoryType
    occurred_at: datetime


class TopupLegRecord(BaseModel):
    transaction_id: UUID
    currency_id: UUID
    amount: Decimal
