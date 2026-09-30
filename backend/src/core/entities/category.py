from enum import StrEnum
from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(Entity, TimestampMixin):
    workspace_id: UUID
    type: CategoryType
    name: str
    icon: str
