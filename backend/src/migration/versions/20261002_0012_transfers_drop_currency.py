"""Drop transfers.currency_id: transfer currency is derived from its wallets.

Revision ID: 20261002_0012
Revises: 20261002_0011
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261002_0012"
down_revision: str | None = "20261002_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Данные не переносятся — решение валютной модели (024–025, design.md изменения `transfers-same-currency`).
    op.execute("TRUNCATE transfers")
    op.drop_column("transfers", "currency_id")


def downgrade() -> None:
    op.add_column("transfers", sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE transfers SET currency_id = wallets.currency_id "
        "FROM wallets WHERE wallets.id = transfers.from_wallet_id"
    )
    op.alter_column("transfers", "currency_id", nullable=False)
    op.create_foreign_key(
        "fk_transfers_currency_id_currencies", "transfers", "currencies", ["currency_id"], ["id"], ondelete="RESTRICT"
    )
