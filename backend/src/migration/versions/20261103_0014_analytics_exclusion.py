"""Флаг исключения операций из аналитики."""

import sqlalchemy as sa
from alembic import op

revision = "20261103_0014"
down_revision = "20261007_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("exclude_from_analytics", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("transactions", "exclude_from_analytics")
