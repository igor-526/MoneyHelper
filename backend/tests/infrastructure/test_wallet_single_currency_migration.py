import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command

from tests.infrastructure.database import alembic_config, run_sql, upgrade_to_head

pytestmark = pytest.mark.infrastructure

PREVIOUS_REVISION = "20261002_0010"
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def at_previous_revision(prepared_database: None) -> Iterator[None]:
    command.downgrade(alembic_config(), PREVIOUS_REVISION)
    try:
        yield
    finally:
        upgrade_to_head()


def _seed_workspace_with_currency(user_id, workspace_id, currency_id) -> list:
    return [
        (
            "INSERT INTO users (id, email, password_hash, token_version, created_at) VALUES ($1, $2, 'x', 0, $3)",
            (user_id, f"{user_id}@example.com", CREATED_AT),
        ),
        (
            "INSERT INTO currencies (id, code, name, decimal_places) VALUES ($1, $2, 'Тест', 2)",
            (currency_id, f"S{uuid4().hex[:8].upper()}"),
        ),
        (
            "INSERT INTO workspaces (id, user_id, name, currency_id, created_at) VALUES ($1, $2, 'W', $3, $4)",
            (workspace_id, user_id, currency_id, CREATED_AT),
        ),
    ]


def test_upgrade_resets_wallets_and_replaces_wallet_currencies_with_currency_id(at_previous_revision: None) -> None:
    user_id, workspace_id, wallet_id, currency_id = (uuid4() for _ in range(4))
    asyncio.run(
        run_sql(
            *_seed_workspace_with_currency(user_id, workspace_id, currency_id),
            (
                "INSERT INTO wallets (id, workspace_id, name, icon, created_at) VALUES ($1, $2, 'A', 'wallet', $3)",
                (wallet_id, workspace_id, CREATED_AT),
            ),
            ("INSERT INTO wallet_currencies (wallet_id, currency_id) VALUES ($1, $2)", (wallet_id, currency_id)),
        )
    )

    command.upgrade(alembic_config(), "20261002_0011")

    try:
        wallet_rows, table_rows, column_rows, foreign_key_rows = asyncio.run(
            run_sql(
                ("SELECT id FROM wallets", ()),
                ("SELECT to_regclass('wallet_currencies') AS name", ()),
                (
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'wallets' AND column_name = 'currency_id'",
                    (),
                ),
                (
                    "SELECT confdeltype FROM pg_constraint WHERE conname = 'fk_wallets_currency_id_currencies'",
                    (),
                ),
            )
        )
        assert wallet_rows == []
        assert table_rows[0]["name"] is None
        assert [row["is_nullable"] for row in column_rows] == ["NO"]
        assert [row["confdeltype"] for row in foreign_key_rows] == [b"r"]
    finally:
        asyncio.run(
            run_sql(
                ("DELETE FROM users WHERE id = $1", (user_id,)),
                ("DELETE FROM currencies WHERE id = $1", (currency_id,)),
            )
        )


def test_downgrade_restores_wallet_currencies_from_currency_id(prepared_database: None) -> None:
    user_id, workspace_id, wallet_id, currency_id = (uuid4() for _ in range(4))
    asyncio.run(
        run_sql(
            *_seed_workspace_with_currency(user_id, workspace_id, currency_id),
            (
                "INSERT INTO wallets (id, workspace_id, name, icon, currency_id, created_at) "
                "VALUES ($1, $2, 'A', 'wallet', $3, $4)",
                (wallet_id, workspace_id, currency_id, CREATED_AT),
            ),
        )
    )

    command.downgrade(alembic_config(), PREVIOUS_REVISION)

    try:
        (rows,) = asyncio.run(run_sql(("SELECT wallet_id, currency_id FROM wallet_currencies", ())))
        assert [(row["wallet_id"], row["currency_id"]) for row in rows] == [(wallet_id, currency_id)]
    finally:
        upgrade_to_head()
        asyncio.run(
            run_sql(
                ("DELETE FROM users WHERE id = $1", (user_id,)),
                ("DELETE FROM currencies WHERE id = $1", (currency_id,)),
            )
        )
