from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Transfer(Entity, TimestampMixin):
    workspace_id: UUID
    from_wallet_id: UUID
    to_wallet_id: UUID
    currency_id: UUID
    amount: Decimal
    occurred_at: datetime
