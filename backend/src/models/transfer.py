from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from models.types import MONEY
from utils.basemodel import metadata

transfers = Table(
    "transfers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("from_wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("to_wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("amount", MONEY, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
    CheckConstraint("from_wallet_id <> to_wallet_id", name="ck_transfers_different_wallets"),
)
