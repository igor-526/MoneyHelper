from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from utils.basemodel import metadata

categories = Table(
    "categories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("type", String(10), nullable=False),
    Column("name", String(100), nullable=False),
    Column("icon", String(50), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type_valid"),
    UniqueConstraint("workspace_id", "type", "name", name="uq_categories_workspace_id_type_name"),
)
