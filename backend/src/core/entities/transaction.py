from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from core.entities.base import Entity, TimestampMixin


class TransactionLeg(BaseModel):
    currency_id: UUID
    amount: Decimal


class Transaction(Entity, TimestampMixin):
    user_id: UUID
    wallet_id: UUID
    category_id: UUID
    legs: tuple[TransactionLeg, ...]
    occurred_at: datetime
