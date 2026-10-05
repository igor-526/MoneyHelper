from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Workspace(Entity, TimestampMixin):
    user_id: UUID
    name: str
    currency_id: UUID
