import asyncio
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command

from tests.infrastructure.database import SRC_DIR, alembic_config, run_sql, upgrade_to_head

pytestmark = pytest.mark.infrastructure

PREVIOUS_REVISION = "20260930_0009"
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_rub_id() -> UUID:
    seeds = json.loads((SRC_DIR / "seeds" / "currencies.json").read_text(encoding="utf-8"))
    return UUID(next(item["id"] for item in seeds if item["code"] == "RUB"))


@pytest.fixture
def at_previous_revision(prepared_database: None) -> Iterator[None]:
    command.downgrade(alembic_config(), PREVIOUS_REVISION)
    try:
        yield
    finally:
        upgrade_to_head()


def test_migration_sets_rub_and_resets_wallets_transactions_and_transfers(at_previous_revision: None) -> None:
    user_id, workspace_id, wallet_a, wallet_b, category_id = (uuid4() for _ in range(5))
    currency_id = uuid4()
    code = f"M{uuid4().hex[:8].upper()}"
    asyncio.run(
        run_sql(
            (
                "INSERT INTO users (id, email, password_hash, token_version, created_at) VALUES ($1, $2, 'x', 0, $3)",
                (user_id, f"{user_id}@example.com", CREATED_AT),
            ),
            (
                "INSERT INTO workspaces (id, user_id, name, created_at) VALUES ($1, $2, 'W', $3)",
                (workspace_id, user_id, CREATED_AT),
            ),
            (
                "INSERT INTO currencies (id, code, name, decimal_places) VALUES ($1, $2, 'Тест', 2)",
                (currency_id, code),
            ),
            (
                "INSERT INTO wallets (id, workspace_id, name, icon, created_at) VALUES ($1, $2, 'A', 'wallet', $3), "
                "($4, $2, 'B', 'wallet', $3)",
                (wallet_a, workspace_id, CREATED_AT, wallet_b),
            ),
            ("INSERT INTO wallet_currencies (wallet_id, currency_id) VALUES ($1, $2)", (wallet_a, currency_id)),
            (
                "INSERT INTO categories (id, workspace_id, type, name, icon, created_at) "
                "VALUES ($1, $2, 'income', 'C', 'wallet', $3)",
                (category_id, workspace_id, CREATED_AT),
            ),
            (
                "INSERT INTO transfers (id, workspace_id, from_wallet_id, to_wallet_id, currency_id, amount, "
                "occurred_at, created_at) VALUES ($1, $2, $3, $4, $5, 1, $6, $6)",
                (uuid4(), workspace_id, wallet_a, wallet_b, currency_id, CREATED_AT),
            ),
        )
    )

    command.upgrade(alembic_config(), "20261002_0010")

    try:
        (workspace_rows, wallet_rows, transfer_rows, category_rows, currency_rows) = asyncio.run(
            run_sql(
                ("SELECT currency_id FROM workspaces WHERE id = $1", (workspace_id,)),
                ("SELECT id FROM wallets", ()),
                ("SELECT id FROM transfers", ()),
                ("SELECT id FROM categories WHERE id = $1", (category_id,)),
                ("SELECT code FROM currencies WHERE id = $1", (_seed_rub_id(),)),
            )
        )
        assert [row["currency_id"] for row in workspace_rows] == [_seed_rub_id()]
        assert wallet_rows == []
        assert transfer_rows == []
        assert len(category_rows) == 1
        assert [row["code"] for row in currency_rows] == ["RUB"]
    finally:
        asyncio.run(
            run_sql(
                ("DELETE FROM users WHERE id = $1", (user_id,)),
                ("DELETE FROM currencies WHERE id = ANY($1)", ([currency_id, _seed_rub_id()],)),
            )
        )
