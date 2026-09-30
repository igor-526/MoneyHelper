"""Add workspaces table; move ownership of wallets/categories/transactions/transfers from user_id to workspace_id.

Revision ID: 20260929_0008
Revises: 20260929_0007
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0008"
down_revision: str | None = "20260929_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCOPED_TABLES = ("wallets", "categories", "transactions", "transfers")


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Существующие тестовые данные не переносятся в дефолтный воркспейс — решение пользователя (design.md
    # изменения `workspaces`, decision 5): реальных пользователей ещё нет. CASCADE очищает и `transaction_legs`,
    # и `wallet_currencies` через уже существующие ON DELETE CASCADE. Таблицы пустые после этого — NOT NULL
    # `workspace_id` ниже не требует бэкофилла.
    op.execute(f"TRUNCATE {', '.join(SCOPED_TABLES)} CASCADE")

    for table in SCOPED_TABLES:
        op.drop_column(table, "user_id")
        op.add_column(
            table,
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
        )

    op.create_unique_constraint("uq_categories_workspace_id_type_name", "categories", ["workspace_id", "type", "name"])


def downgrade() -> None:
    for table in SCOPED_TABLES:
        op.drop_column(table, "workspace_id")
        op.add_column(
            table,
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
        )

    op.create_unique_constraint("uq_categories_user_id_type_name", "categories", ["user_id", "type", "name"])
    op.drop_table("workspaces")
