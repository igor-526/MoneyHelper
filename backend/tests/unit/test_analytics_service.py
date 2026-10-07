from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Wallet, Workspace
from core.exceptions import ClientError, NotFoundError
from core.services.analytics import AnalyticsService
from tests.fakes import (
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
)

DATE_FROM = datetime(2026, 1, 1)
DATE_TO = datetime(2026, 1, 31)
IN_RANGE = datetime(2026, 1, 15)
OUT_OF_RANGE = datetime(2026, 3, 15)

Buckets = dict[UUID | date, tuple[Decimal, Decimal]]


class Environment:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.wallets = InMemoryWalletRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.service = AnalyticsService(self.transactions, self.currencies, self.wallets, self.workspaces)

    async def make_currency(self, code: str, decimal_places: int = 2) -> Currency:
        currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
        await self.currencies.upsert_many([currency])
        return currency

    async def make_workspace(self, currency: Currency) -> UUID:
        workspace = Workspace(id=uuid4(), user_id=uuid4(), name="Т", currency_id=currency.id, created_at=IN_RANGE)
        self.workspaces.seed(workspace)
        return workspace.id

    async def make_wallet(self, workspace_id: UUID, currency: Currency) -> UUID:
        wallet = Wallet(
            id=uuid4(),
            workspace_id=workspace_id,
            name="К",
            icon="wallet",
            currency_id=currency.id,
            created_at=IN_RANGE,
        )
        return (await self.wallets.add(wallet)).id

    async def make_category(self, workspace_id: UUID, type: CategoryType) -> UUID:
        category = Category(
            id=uuid4(), workspace_id=workspace_id, type=type, name=f"К {uuid4()}", icon="wallet", created_at=IN_RANGE
        )
        return (await self.categories.add(category)).id

    async def add_operation(
        self,
        workspace_id: UUID,
        wallet_id: UUID,
        category_id: UUID,
        legs: dict[UUID, str],
        occurred_at: datetime = IN_RANGE,
    ) -> None:
        await self.transactions.add(
            Transaction(
                id=uuid4(),
                workspace_id=workspace_id,
                wallet_id=wallet_id,
                category_id=category_id,
                legs=tuple(TransactionLeg(currency_id=c, amount=Decimal(a)) for c, a in legs.items()),
                occurred_at=occurred_at,
                created_at=occurred_at,
            )
        )

    async def analytics(
        self,
        workspace_id: UUID,
        *,
        display: Currency | None = None,
        group_by: str = "wallet",
        wallet_id: UUID | None = None,
        category_id: UUID | None = None,
        currency_id: UUID | None = None,
        type: CategoryType | None = None,
    ) -> tuple[UUID, Buckets, list[UUID]]:
        display_currency_id, buckets, unconverted = await self.service.get_analytics(
            workspace_id,
            display_currency_id=display.id if display is not None else None,
            date_from=DATE_FROM,
            date_to=DATE_TO,
            group_by=group_by,
            wallet_id=wallet_id,
            category_id=category_id,
            currency_id=currency_id,
            type=type,
        )
        return display_currency_id, {key: (income, expense) for key, income, expense in buckets}, unconverted


class Scenario:
    """Воркспейс в RUB с кошельком в CNY и пополнением 1000 RUB / 100 CNY (курс 10)."""

    def __init__(self, env: Environment) -> None:
        self.env = env

    @classmethod
    async def create(cls) -> Scenario:
        scenario = cls(Environment())
        env = scenario.env
        scenario.rub = await env.make_currency("RUB")
        scenario.cny = await env.make_currency("CNY")
        scenario.workspace_id = await env.make_workspace(scenario.rub)
        scenario.rub_wallet = await env.make_wallet(scenario.workspace_id, scenario.rub)
        scenario.cny_wallet = await env.make_wallet(scenario.workspace_id, scenario.cny)
        scenario.income = await env.make_category(scenario.workspace_id, CategoryType.INCOME)
        scenario.expense = await env.make_category(scenario.workspace_id, CategoryType.EXPENSE)
        return scenario

    async def topup_cny(self, rub: str, cny: str, occurred_at: datetime = IN_RANGE) -> None:
        await self.env.add_operation(
            self.workspace_id, self.cny_wallet, self.income, {self.rub.id: rub, self.cny.id: cny}, occurred_at
        )

    async def spend_cny(self, amount: str) -> None:
        await self.env.add_operation(self.workspace_id, self.cny_wallet, self.expense, {self.cny.id: amount})

    rub: Currency
    cny: Currency
    workspace_id: UUID
    rub_wallet: UUID
    cny_wallet: UUID
    income: UUID
    expense: UUID


async def test_default_display_currency_is_workspace_currency() -> None:
    s = await Scenario.create()
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "40"})

    display_id, buckets, unconverted = await s.env.analytics(s.workspace_id)

    assert display_id == s.rub.id
    assert buckets == {s.rub_wallet: (Decimal("0"), Decimal("40"))}
    assert unconverted == []


async def test_topup_counts_wallet_leg_once_converted_to_workspace_currency() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100")

    _, buckets, unconverted = await s.env.analytics(s.workspace_id)

    assert buckets == {s.cny_wallet: (Decimal("1000.00"), Decimal("0.00"))}
    assert unconverted == []


async def test_same_currency_topup_is_counted_without_conversion() -> None:
    s = await Scenario.create()
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.income, {s.rub.id: "500"})

    _, buckets, _ = await s.env.analytics(s.workspace_id)

    assert buckets == {s.rub_wallet: (Decimal("500"), Decimal("0"))}


async def test_expense_converted_by_average_topup_rate() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100")
    await s.spend_cny("30")

    _, buckets, _ = await s.env.analytics(s.workspace_id, type=CategoryType.EXPENSE)

    assert buckets == {s.cny_wallet: (Decimal("0.00"), Decimal("300.00"))}


async def test_rate_is_simple_average_not_weighted() -> None:
    s = await Scenario.create()
    await s.topup_cny("100", "10")
    await s.topup_cny("1000", "10")
    await s.spend_cny("10")

    _, buckets, _ = await s.env.analytics(s.workspace_id, type=CategoryType.EXPENSE)

    assert buckets[s.cny_wallet][1] == Decimal("550.00")


async def test_topup_outside_range_provides_rate() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100", OUT_OF_RANGE)
    await s.spend_cny("30")

    _, buckets, unconverted = await s.env.analytics(s.workspace_id)

    assert buckets == {s.cny_wallet: (Decimal("0.00"), Decimal("300.00"))}
    assert unconverted == []


async def test_currency_without_topups_is_unconverted_and_does_not_fail_request() -> None:
    s = await Scenario.create()
    await s.spend_cny("30")
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "5"})

    _, buckets, unconverted = await s.env.analytics(s.workspace_id)

    assert buckets == {s.rub_wallet: (Decimal("0"), Decimal("5"))}
    assert unconverted == [s.cny.id]


async def test_display_in_wallet_currency_converts_workspace_currency_wallets() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100")
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "50"})

    display_id, buckets, unconverted = await s.env.analytics(s.workspace_id, display=s.cny)

    assert display_id == s.cny.id
    assert buckets[s.cny_wallet] == (Decimal("100"), Decimal("0"))
    assert buckets[s.rub_wallet] == (Decimal("0.00"), Decimal("5.00"))
    assert unconverted == []


async def test_display_currency_unrelated_to_workspace_is_rejected() -> None:
    s = await Scenario.create()
    usd = await s.env.make_currency("USD")

    with pytest.raises(ClientError):
        await s.env.analytics(s.workspace_id, display=usd)


async def test_display_currency_unknown_to_directory_is_rejected() -> None:
    s = await Scenario.create()

    with pytest.raises(ClientError):
        await s.env.service.get_analytics(
            s.workspace_id,
            display_currency_id=uuid4(),
            date_from=DATE_FROM,
            date_to=DATE_TO,
            group_by="wallet",
            wallet_id=None,
            category_id=None,
            currency_id=None,
            type=None,
        )


async def test_unknown_workspace_raises_not_found() -> None:
    env = Environment()

    with pytest.raises(NotFoundError):
        await env.analytics(uuid4())


async def test_date_from_after_date_to_raises_client_error() -> None:
    s = await Scenario.create()

    with pytest.raises(ClientError):
        await s.env.service.get_analytics(
            s.workspace_id,
            display_currency_id=None,
            date_from=DATE_TO,
            date_to=DATE_FROM,
            group_by="wallet",
            wallet_id=None,
            category_id=None,
            currency_id=None,
            type=None,
        )


async def test_without_date_range_counts_all_time() -> None:
    s = await Scenario.create()
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "40"})
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "60"}, OUT_OF_RANGE)

    _, buckets, _ = await s.env.service.get_analytics(
        s.workspace_id,
        display_currency_id=None,
        date_from=None,
        date_to=None,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert [(key, expense) for key, _, expense in buckets] == [(s.rub_wallet, Decimal("100"))]


async def test_groups_by_category() -> None:
    s = await Scenario.create()
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.income, {s.rub.id: "100"})
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "30"})

    _, buckets, _ = await s.env.analytics(s.workspace_id, group_by="category")

    assert buckets == {s.income: (Decimal("100"), Decimal("0")), s.expense: (Decimal("0"), Decimal("30"))}


async def test_groups_by_wallet_currency() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100")
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.income, {s.rub.id: "100"})

    _, buckets, _ = await s.env.analytics(s.workspace_id, group_by="currency")

    assert buckets == {s.rub.id: (Decimal("100"), Decimal("0")), s.cny.id: (Decimal("1000.00"), Decimal("0.00"))}


async def test_currency_filter_means_wallet_currency() -> None:
    s = await Scenario.create()
    await s.topup_cny("1000", "100")
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.income, {s.rub.id: "100"})

    _, buckets, _ = await s.env.analytics(s.workspace_id, currency_id=s.rub.id)

    assert buckets == {s.rub_wallet: (Decimal("100"), Decimal("0"))}


async def test_filters_narrow_operations_but_not_rate_topups() -> None:
    s = await Scenario.create()
    other_cny_wallet = await s.env.make_wallet(s.workspace_id, s.cny)
    await s.topup_cny("1000", "100")
    await s.env.add_operation(s.workspace_id, other_cny_wallet, s.expense, {s.cny.id: "10"})

    _, buckets, unconverted = await s.env.analytics(s.workspace_id, wallet_id=other_cny_wallet)

    assert buckets == {other_cny_wallet: (Decimal("0.00"), Decimal("100.00"))}
    assert unconverted == []


async def test_bucket_total_rounded_once() -> None:
    s = await Scenario.create()
    await s.topup_cny("1", "3")
    for _ in range(3):
        await s.spend_cny("1")

    _, buckets, _ = await s.env.analytics(s.workspace_id)

    assert buckets[s.cny_wallet][1] == Decimal("1.00")


async def test_other_workspace_data_does_not_participate() -> None:
    s = await Scenario.create()
    other_workspace_id = await s.env.make_workspace(s.rub)
    other_wallet = await s.env.make_wallet(other_workspace_id, s.cny)
    other_income = await s.env.make_category(other_workspace_id, CategoryType.INCOME)
    await s.env.add_operation(other_workspace_id, other_wallet, other_income, {s.rub.id: "1000", s.cny.id: "100"})
    await s.spend_cny("30")

    _, buckets, unconverted = await s.env.analytics(s.workspace_id)

    assert buckets == {}
    assert unconverted == [s.cny.id]


async def test_groups_by_local_day() -> None:
    s = await Scenario.create()
    next_day = datetime(2026, 1, 16, 0, 30)
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "10"}, IN_RANGE)
    await s.env.add_operation(s.workspace_id, s.rub_wallet, s.expense, {s.rub.id: "20"}, next_day)

    _, buckets, _ = await s.env.analytics(s.workspace_id, group_by="day", type=CategoryType.EXPENSE)

    assert buckets == {
        date(2026, 1, 15): (Decimal("0"), Decimal("10")),
        date(2026, 1, 16): (Decimal("0"), Decimal("20")),
    }
