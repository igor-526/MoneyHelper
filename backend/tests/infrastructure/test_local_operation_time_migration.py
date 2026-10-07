import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command

from tests.infrastructure.database import alembic_config, run_sql, upgrade_to_head

pytestmark = pytest.mark.infrastructure

PREVIOUS_REVISION = "20261002_0012"


@pytest.fixture
def at_previous_revision(prepared_database: None) -> Iterator[None]:
    command.downgrade(alembic_config(), PREVIOUS_REVISION)
    try:
        yield
    finally:
        upgrade_to_head()


def test_upgrade_preserves_operations_and_shanghai_dates(at_previous_revision: None) -> None:
    user_id, currency_id, workspace_id, wallet_a, wallet_b, category_id, transaction_a, transaction_b, transfer_id = (
        uuid4() for _ in range(9)
    )
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    before_midnight = datetime(2026, 10, 7, 15, 30, tzinfo=UTC)
    after_midnight = datetime(2026, 10, 7, 16, 30, tzinfo=UTC)
    asyncio.run(
        run_sql(
            ("SET TIME ZONE 'Europe/Moscow'", ()),
            (
                "INSERT INTO users (id, email, password_hash, token_version, created_at) VALUES ($1, $2, 'x', 0, $3)",
                (user_id, f"{user_id}@example.com", created_at),
            ),
            (
                "INSERT INTO currencies (id, code, name, decimal_places) VALUES ($1, $2, 'Тест', 2)",
                (currency_id, f"M{uuid4().hex[:8].upper()}"),
            ),
            (
                "INSERT INTO workspaces (id, user_id, name, currency_id, created_at) VALUES ($1, $2, 'W', $3, $4)",
                (workspace_id, user_id, currency_id, created_at),
            ),
            (
                "INSERT INTO wallets (id, workspace_id, name, icon, currency_id, created_at) VALUES "
                "($1, $2, 'A', 'wallet', $3, $4), ($5, $2, 'B', 'wallet', $3, $4)",
                (wallet_a, workspace_id, currency_id, created_at, wallet_b),
            ),
            (
                "INSERT INTO categories (id, workspace_id, type, name, icon, created_at) "
                "VALUES ($1, $2, 'expense', 'Расход', 'wallet', $3)",
                (category_id, workspace_id, created_at),
            ),
            (
                "INSERT INTO transactions "
                "(id, workspace_id, wallet_id, category_id, occurred_at, comment, created_at) "
                "VALUES ($1, $2, $3, $4, $5, 'до полуночи', $7), "
                "($6, $2, $3, $4, $8, 'после полуночи', $7)",
                (
                    transaction_a,
                    workspace_id,
                    wallet_a,
                    category_id,
                    before_midnight,
                    transaction_b,
                    created_at,
                    after_midnight,
                ),
            ),
            (
                "INSERT INTO transaction_legs (transaction_id, currency_id, amount) "
                "VALUES ($1, $3, 10.25), ($2, $3, 20.50)",
                (transaction_a, transaction_b, currency_id),
            ),
            (
                "INSERT INTO transfers (id, workspace_id, from_wallet_id, to_wallet_id, amount, occurred_at, "
                "created_at) VALUES ($1, $2, $3, $4, 5, $5, $6)",
                (transfer_id, workspace_id, wallet_a, wallet_b, after_midnight, created_at),
            ),
        )
    )

    command.upgrade(alembic_config(), "head")

    try:
        rows, legs, column_type, transfer_table = asyncio.run(
            run_sql(
                (
                    "SELECT id, workspace_id, wallet_id, category_id, occurred_at, comment, created_at "
                    "FROM transactions WHERE id = ANY($1::uuid[]) ORDER BY occurred_at",
                    ([transaction_a, transaction_b],),
                ),
                (
                    "SELECT transaction_id, currency_id, amount FROM transaction_legs "
                    "WHERE transaction_id = ANY($1::uuid[]) ORDER BY amount",
                    ([transaction_a, transaction_b],),
                ),
                (
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'transactions' AND column_name = 'occurred_at'",
                    (),
                ),
                ("SELECT to_regclass('public.transfers') AS name", ()),
            )
        )
        assert [row["id"] for row in rows] == [transaction_a, transaction_b]
        assert [row["occurred_at"] for row in rows] == [
            datetime(2026, 10, 7, 23, 30),
            datetime(2026, 10, 8, 0, 30),
        ]
        assert [row["comment"] for row in rows] == ["до полуночи", "после полуночи"]
        assert all(row["workspace_id"] == workspace_id for row in rows)
        assert all(row["wallet_id"] == wallet_a for row in rows)
        assert all(row["category_id"] == category_id for row in rows)
        assert all(row["created_at"] == created_at for row in rows)
        assert [(row["transaction_id"], row["currency_id"], row["amount"]) for row in legs] == [
            (transaction_a, currency_id, Decimal("10.25000000")),
            (transaction_b, currency_id, Decimal("20.50000000")),
        ]
        assert [row["data_type"] for row in column_type] == ["timestamp without time zone"]
        assert [row["name"] for row in transfer_table] == [None]
    finally:
        asyncio.run(
            run_sql(
                ("DELETE FROM users WHERE id = $1", (user_id,)),
                ("DELETE FROM currencies WHERE id = $1", (currency_id,)),
            )
        )
