from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Wallet(Entity, TimestampMixin):
    workspace_id: UUID
    name: str
    icon: str
    currency_id: UUID
