from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Transaction(Entity, TimestampMixin):
    user_id: UUID
    wallet_id: UUID
    category_id: UUID
    currency_id: UUID
    amount: Decimal
    occurred_at: datetime
