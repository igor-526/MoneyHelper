"""Add currencies table.

Revision ID: 20260929_0003
Revises: 20260929_0002
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0003"
down_revision: str | None = "20260929_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=10), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("decimal_places", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("code = upper(code)", name="ck_currencies_code_uppercase"),
        sa.CheckConstraint("decimal_places BETWEEN 0 AND 8", name="ck_currencies_decimal_places_range"),
    )


def downgrade() -> None:
    op.drop_table("currencies")
