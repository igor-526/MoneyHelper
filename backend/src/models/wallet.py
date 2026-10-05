from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID

from utils.basemodel import metadata

wallets = Table(
    "wallets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("icon", String(50), nullable=False),
    Column("currency_id", UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
)
