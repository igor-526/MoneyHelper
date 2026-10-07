import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command

from tests.infrastructure.database import alembic_config, run_sql, upgrade_to_head

pytestmark = pytest.mark.infrastructure

PREVIOUS_REVISION = "20261002_0011"
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def at_previous_revision(prepared_database: None) -> Iterator[None]:
    command.downgrade(alembic_config(), PREVIOUS_REVISION)
    try:
        yield
    finally:
        upgrade_to_head()


def _seed_wallets(user_id, workspace_id, currency_id, wallet_ids) -> list:
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
        *(
            (
                "INSERT INTO wallets (id, workspace_id, name, icon, currency_id, created_at) "
                "VALUES ($1, $2, 'A', 'wallet', $3, $4)",
                (wallet_id, workspace_id, currency_id, CREATED_AT),
            )
            for wallet_id in wallet_ids
        ),
    ]


def _cleanup(user_id, currency_id):
    return (
        ("DELETE FROM users WHERE id = $1", (user_id,)),
        ("DELETE FROM currencies WHERE id = $1", (currency_id,)),
    )


def test_upgrade_resets_transfers_and_drops_currency_id(at_previous_revision: None) -> None:
    user_id, workspace_id, currency_id, from_wallet_id, to_wallet_id, transfer_id = (uuid4() for _ in range(6))
    asyncio.run(
        run_sql(
            *_seed_wallets(user_id, workspace_id, currency_id, (from_wallet_id, to_wallet_id)),
            (
                "INSERT INTO transfers (id, workspace_id, from_wallet_id, to_wallet_id, currency_id, amount, "
                "occurred_at, created_at) VALUES ($1, $2, $3, $4, $5, 10, $6, $6)",
                (transfer_id, workspace_id, from_wallet_id, to_wallet_id, currency_id, CREATED_AT),
            ),
        )
    )

    command.upgrade(alembic_config(), "20261002_0012")

    try:
        transfer_rows, column_rows = asyncio.run(
            run_sql(
                ("SELECT id FROM transfers", ()),
                (
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'transfers' AND column_name = 'currency_id'",
                    (),
                ),
            )
        )
        assert transfer_rows == []
        assert column_rows == []
    finally:
        asyncio.run(run_sql(*_cleanup(user_id, currency_id)))


def test_downgrade_restores_currency_id_from_wallet(prepared_database: None) -> None:
    user_id, workspace_id, currency_id, from_wallet_id, to_wallet_id, transfer_id = (uuid4() for _ in range(6))
    command.downgrade(alembic_config(), "20261002_0012")
    asyncio.run(
        run_sql(
            *_seed_wallets(user_id, workspace_id, currency_id, (from_wallet_id, to_wallet_id)),
            (
                "INSERT INTO transfers (id, workspace_id, from_wallet_id, to_wallet_id, amount, occurred_at, "
                "created_at) VALUES ($1, $2, $3, $4, 10, $5, $5)",
                (transfer_id, workspace_id, from_wallet_id, to_wallet_id, CREATED_AT),
            ),
        )
    )

    command.downgrade(alembic_config(), PREVIOUS_REVISION)

    try:
        (rows,) = asyncio.run(run_sql(("SELECT currency_id FROM transfers", ())))
        assert [row["currency_id"] for row in rows] == [currency_id]
    finally:
        upgrade_to_head()
        asyncio.run(run_sql(*_cleanup(user_id, currency_id)))
