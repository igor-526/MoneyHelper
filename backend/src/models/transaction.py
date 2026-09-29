from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, PrimaryKeyConstraint, Table
from sqlalchemy.dialects.postgresql import UUID

from models.types import MONEY
from utils.basemodel import metadata

transactions = Table(
    "transactions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
)

transaction_legs = Table(
    "transaction_legs",
    metadata,
    Column("transaction_id", UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
    Column("currency_id", UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False),
    Column("amount", MONEY, nullable=False),
    PrimaryKeyConstraint("transaction_id", "currency_id"),
    CheckConstraint("amount > 0", name="ck_transaction_legs_amount_positive"),
)
