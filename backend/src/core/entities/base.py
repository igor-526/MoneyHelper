from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Entity(BaseModel):
    id: UUID


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
