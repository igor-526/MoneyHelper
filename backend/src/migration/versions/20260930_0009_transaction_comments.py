"""Add nullable comment column to transactions.

Revision ID: 20260930_0009
Revises: 20260929_0008
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260930_0009"
down_revision: str | None = "20260929_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("comment", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "comment")
