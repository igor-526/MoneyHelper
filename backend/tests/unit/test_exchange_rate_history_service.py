from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Wallet, Workspace
from core.exceptions import ClientError, NotFoundError
from core.services.exchange_rate_history import ExchangeRateHistoryService
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)


class Environment:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.wallets = InMemoryWalletRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.service = ExchangeRateHistoryService(self.transactions, self.currencies, self.wallets, self.workspaces)
        self.workspace_id = uuid4()
        self.rub = Currency(id=uuid4(), code="RUB", name="Рубль", decimal_places=2)
        self.cny = Currency(id=uuid4(), code="CNY", name="Юань", decimal_places=2)

    async def setup(self) -> None:
        await self.currencies.upsert_many([self.rub, self.cny])
        self.workspaces.seed(
            Workspace(
                id=self.workspace_id,
                user_id=uuid4(),
                name="Тест",
                currency_id=self.rub.id,
                created_at=datetime(2026, 1, 1),
            )
        )
        self.wallet_id = (
            await self.wallets.add(
                Wallet(
                    id=uuid4(),
                    workspace_id=self.workspace_id,
                    name="CNY",
                    icon="wallet",
                    currency_id=self.cny.id,
                    created_at=datetime(2026, 1, 1),
                )
            )
        ).id
        self.income_id = (
            await self.categories.add(
                Category(
                    id=uuid4(),
                    workspace_id=self.workspace_id,
                    type=CategoryType.INCOME,
                    name="Пополнение",
                    icon="wallet",
                    created_at=datetime(2026, 1, 1),
                )
            )
        ).id

    async def add_topup(self, rub: str, cny: str, occurred_at: datetime) -> None:
        await self.transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=self.workspace_id,
                wallet_id=self.wallet_id,
                category_id=self.income_id,
                legs=(
                    TransactionLeg(currency_id=self.rub.id, amount=Decimal(rub)),
                    TransactionLeg(currency_id=self.cny.id, amount=Decimal(cny)),
                ),
                occurred_at=occurred_at,
                created_at=occurred_at,
            )
        )

    async def history(self, date_from: datetime | None = None, date_to: datetime | None = None):
        return await self.service.get_history(
            self.workspace_id,
            base_currency_id=self.cny.id,
            date_from=date_from,
            date_to=date_to,
        )


async def test_daily_rates_are_simple_averages_and_sorted() -> None:
    env = Environment()
    await env.setup()
    await env.add_topup("140", "10", datetime(2026, 1, 2, 18))
    await env.add_topup("120", "10", datetime(2026, 1, 1, 12))
    await env.add_topup("100", "10", datetime(2026, 1, 2, 9))

    history = await env.history()

    assert history.base_currency_id == env.cny.id
    assert history.quote_currency_id == env.rub.id
    assert [(point.date.isoformat(), point.rate) for point in history.points] == [
        ("2026-01-01", Decimal("12.0000000000")),
        ("2026-01-02", Decimal("12.0000000000")),
    ]


async def test_range_filters_samples_before_daily_aggregation() -> None:
    env = Environment()
    await env.setup()
    await env.add_topup("100", "10", datetime(2026, 1, 1, 12))
    await env.add_topup("140", "10", datetime(2026, 1, 2, 12))

    history = await env.history(datetime(2026, 1, 2), datetime(2026, 1, 2, 23, 59, 59))

    assert [(point.date.isoformat(), point.rate) for point in history.points] == [
        ("2026-01-02", Decimal("14.0000000000"))
    ]


async def test_rub_and_unrelated_currency_are_rejected() -> None:
    env = Environment()
    await env.setup()
    unrelated = Currency(id=uuid4(), code="USD", name="Доллар", decimal_places=2)
    await env.currencies.upsert_many([unrelated])

    for currency_id in (env.rub.id, unrelated.id, uuid4()):
        with pytest.raises(ClientError):
            await env.service.get_history(env.workspace_id, base_currency_id=currency_id, date_from=None, date_to=None)


async def test_missing_workspace_is_not_found() -> None:
    env = Environment()
    await env.setup()

    with pytest.raises(NotFoundError):
        await env.service.get_history(uuid4(), base_currency_id=env.cny.id, date_from=None, date_to=None)


async def test_other_workspace_topups_are_not_used() -> None:
    env = Environment()
    await env.setup()
    await env.add_topup("100", "10", datetime(2026, 1, 1))
    other_workspace_id = uuid4()
    env.workspaces.seed(
        Workspace(
            id=other_workspace_id,
            user_id=uuid4(),
            name="Другой",
            currency_id=env.cny.id,
            created_at=datetime(2026, 1, 1),
        )
    )

    history = await env.service.get_history(
        other_workspace_id, base_currency_id=env.cny.id, date_from=None, date_to=None
    )

    assert history.points == ()
