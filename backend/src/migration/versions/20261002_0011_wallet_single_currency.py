"""Replace wallet_currencies with wallets.currency_id; reset wallets, transactions and transfers.

Revision ID: 20261002_0011
Revises: 20261002_0010
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261002_0011"
down_revision: str | None = "20261002_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESET_TABLES = ("wallets", "transactions", "transfers")


def upgrade() -> None:
    # Данные не переносятся — решение пользователя (design.md изменения `wallet-single-currency`, decision 2):
    # у кошелька с несколькими валютами нет однозначной единственной валюты. CASCADE очищает `wallet_currencies`
    # и `transaction_legs`; после очистки `currency_id` добавляется сразу как NOT NULL.
    op.execute(f"TRUNCATE {', '.join(RESET_TABLES)} CASCADE")

    op.drop_table("wallet_currencies")
    op.add_column("wallets", sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "fk_wallets_currency_id_currencies", "wallets", "currencies", ["currency_id"], ["id"], ondelete="RESTRICT"
    )


def downgrade() -> None:
    op.create_table(
        "wallet_currencies",
        sa.Column(
            "wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "currency_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("currencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("wallet_id", "currency_id"),
    )
    op.execute("INSERT INTO wallet_currencies (wallet_id, currency_id) SELECT id, currency_id FROM wallets")
    op.drop_constraint("fk_wallets_currency_id_currencies", "wallets", type_="foreignkey")
    op.drop_column("wallets", "currency_id")
