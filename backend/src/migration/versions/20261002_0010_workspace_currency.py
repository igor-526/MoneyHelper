"""Add workspaces.currency_id; reset wallets, transactions and transfers.

Revision ID: 20261002_0010
Revises: 20260930_0009
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261002_0010"
down_revision: str | None = "20260930_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Тот же UUID, что у RUB в seeds/currencies.json: миграция идёт до сидирования, а FK требует существующую строку.
DEFAULT_CURRENCY_ID = "1c9586e7-c3d6-465b-8efb-81f74a2dc28b"
DEFAULT_CURRENCY_CODE = "RUB"
RESET_TABLES = ("wallets", "transactions", "transfers")


def upgrade() -> None:
    # Данные не переносятся — решение пользователя (design.md изменения `workspace-currency`, decision 5):
    # ноги пополнений и курсы старой модели теряют смысл. CASCADE очищает `wallet_currencies` и `transaction_legs`.
    op.execute(f"TRUNCATE {', '.join(RESET_TABLES)} CASCADE")

    op.add_column("workspaces", sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        sa.text(
            """
            INSERT INTO currencies (id, code, name, decimal_places)
            SELECT CAST(:id AS uuid), :code, 'Российский рубль', 2
            WHERE EXISTS (SELECT 1 FROM workspaces)
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=DEFAULT_CURRENCY_ID, code=DEFAULT_CURRENCY_CODE)
    )
    op.execute(sa.text("UPDATE workspaces SET currency_id = CAST(:id AS uuid)").bindparams(id=DEFAULT_CURRENCY_ID))
    op.alter_column("workspaces", "currency_id", nullable=False)
    op.create_foreign_key(
        "fk_workspaces_currency_id_currencies",
        "workspaces",
        "currencies",
        ["currency_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_workspaces_currency_id_currencies", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "currency_id")
