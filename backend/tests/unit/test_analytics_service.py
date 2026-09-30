from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg
from core.exceptions import ClientError
from core.services.analytics import AnalyticsService
from tests.fakes import InMemoryCategoryRepository, InMemoryCurrencyRepository, InMemoryTransactionRepository

DATE_FROM = datetime(2026, 1, 1, tzinfo=UTC)
DATE_TO = datetime(2026, 1, 31, tzinfo=UTC)
IN_RANGE = datetime(2026, 1, 15, tzinfo=UTC)


class Environment:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.service = AnalyticsService(self.transactions, self.currencies)

    async def make_currency(self, code: str = "RUB", decimal_places: int = 2) -> Currency:
        currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
        await self.currencies.upsert_many([currency])
        return currency

    async def make_category(self, workspace_id: UUID, type: CategoryType) -> Category:
        category = Category(
            id=uuid4(),
            workspace_id=workspace_id,
            type=type,
            name=f"Категория {uuid4()}",
            icon="wallet",
            created_at=IN_RANGE,
        )
        return await self.categories.add(category)

    async def add_transaction(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        currency_id: UUID,
        amount: Decimal,
        occurred_at: datetime = IN_RANGE,
    ) -> Transaction:
        transaction = Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=currency_id, amount=amount),),
            occurred_at=occurred_at,
            created_at=occurred_at,
        )
        return await self.transactions.add(transaction)

    async def add_topup(
        self,
        workspace_id: UUID,
        *,
        wallet_id: UUID,
        category_id: UUID,
        legs: tuple[TransactionLeg, ...],
        occurred_at: datetime = IN_RANGE,
    ) -> Transaction:
        transaction = Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=legs,
            occurred_at=occurred_at,
            created_at=occurred_at,
        )
        return await self.transactions.add(transaction)


async def test_groups_by_wallet() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    wallet_a, wallet_b = uuid4(), uuid4()
    await env.add_transaction(
        workspace_id, wallet_id=wallet_a, category_id=income.id, currency_id=currency.id, amount=Decimal("100")
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet_b, category_id=income.id, currency_id=currency.id, amount=Decimal("50")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == []
    by_key = {key: (income_sum, expense_sum) for key, income_sum, expense_sum in buckets}
    assert by_key[wallet_a] == (Decimal("100"), Decimal("0"))
    assert by_key[wallet_b] == (Decimal("50"), Decimal("0"))


async def test_groups_by_category() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    expense = await env.make_category(workspace_id, CategoryType.EXPENSE)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount=Decimal("100")
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=expense.id, currency_id=currency.id, amount=Decimal("30")
    )

    buckets, _ = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="category",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    by_key = {key: (income_sum, expense_sum) for key, income_sum, expense_sum in buckets}
    assert by_key[income.id] == (Decimal("100"), Decimal("0"))
    assert by_key[expense.id] == (Decimal("0"), Decimal("30"))


async def test_groups_by_currency() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub = await env.make_currency("RUB")
    cny = await env.make_currency("CNY")
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=rub.id, amount=Decimal("100")
    )
    # Один охват курса, чтобы CNY была конвертируема.
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=rub.id, amount=Decimal("10000")),
            TransactionLeg(currency_id=cny.id, amount=Decimal("780")),
        ),
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=cny.id, amount=Decimal("78")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=rub.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="currency",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == []
    by_key = {key: (income_sum, expense_sum) for key, income_sum, expense_sum in buckets}
    # 100 (rub, без конвертации) + 10000 (rub-нога пополнения, тоже транзакция дохода) = 10100
    assert by_key[rub.id][0] == Decimal("10100")
    # Бакет по исходной валюте CNY, но суммы всегда в валюте отображения: курс 10000/780;
    # 780 (cny-нога пополнения) * курс = 10000, плюс 78 (отдельная операция) * курс = 1000 => 11000
    assert by_key[cny.id][0] == Decimal("11000")


async def test_conversion_by_single_topup_rate_reproducible_example() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency_a = await env.make_currency("A")
    currency_b = await env.make_currency("B", decimal_places=8)
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    expense = await env.make_category(workspace_id, CategoryType.EXPENSE)
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=currency_a.id, amount=Decimal("10000")),
            TransactionLeg(currency_id=currency_b.id, amount=Decimal("780")),
        ),
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=expense.id, currency_id=currency_a.id, amount=Decimal("1000")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency_b.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == []
    [(_, income_sum, expense_sum)] = buckets
    # Пополнение само тоже операция дохода: B-нога 780 без конвертации + A-нога 10000 * (780/10000) = 780 => 1560.
    # Расход — отдельная операция: 1000 * (780/10000) = 78.
    assert income_sum == Decimal("1560.00000000")
    assert expense_sum == Decimal("78.00000000")


async def test_rate_averaged_across_multiple_topups_not_weighted() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency_a = await env.make_currency("A")
    currency_b = await env.make_currency("B")
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    expense = await env.make_category(workspace_id, CategoryType.EXPENSE)
    # Курс 1: 10 B за 100 A => 0.1
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=currency_a.id, amount=Decimal("100")),
            TransactionLeg(currency_id=currency_b.id, amount=Decimal("10")),
        ),
    )
    # Курс 2: 1000 B за 1000 A => 1 (сильно другой вес по сумме)
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=currency_a.id, amount=Decimal("1000")),
            TransactionLeg(currency_id=currency_b.id, amount=Decimal("1000")),
        ),
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=expense.id, currency_id=currency_a.id, amount=Decimal("100")
    )

    buckets, _ = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency_b.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    # Простое среднее (0.1 + 1) / 2 = 0.55, не средневзвешенное (которое дало бы иной результат, например
    # 0.1 * 100/1100 + 1 * 1000/1100 ≈ 0.918, если бы взвешивали по сумме source-ноги).
    [(_, _, expense_sum)] = buckets
    assert expense_sum == Decimal("100") * Decimal("0.55")


async def test_display_currency_does_not_require_rate_lookup() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount=Decimal("42")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == []
    [(_, income_sum, expense_sum)] = buckets
    assert income_sum == Decimal("42")
    assert expense_sum == Decimal("0")


async def test_currency_without_rate_excluded_from_sums_without_error() -> None:
    env = Environment()
    workspace_id = uuid4()
    display = await env.make_currency("RUB")
    other = await env.make_currency("CNY")
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=other.id, amount=Decimal("100")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=display.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert buckets == []
    assert unconverted == [other.id]


async def test_currency_with_found_rate_not_in_unconverted() -> None:
    env = Environment()
    workspace_id = uuid4()
    display = await env.make_currency("RUB")
    convertible = await env.make_currency("CNY")
    unconvertible = await env.make_currency("USD")
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=display.id, amount=Decimal("100")),
            TransactionLeg(currency_id=convertible.id, amount=Decimal("10")),
        ),
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=convertible.id, amount=Decimal("5")
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=unconvertible.id, amount=Decimal("5")
    )

    _, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=display.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == [unconvertible.id]


async def test_bucket_total_rounded_once_not_per_operation() -> None:
    env = Environment()
    workspace_id = uuid4()
    display = await env.make_currency("RUB", decimal_places=2)
    source = await env.make_currency("CNY")
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    expense = await env.make_category(workspace_id, CategoryType.EXPENSE)
    # Курс ровно 1/3, чтобы суммы отдельных операций округлялись иначе, чем их сумма. Пополнение оформлено
    # под категорией расхода, чтобы его собственные ноги не смешивались с проверяемой корзиной дохода.
    await env.add_topup(
        workspace_id,
        wallet_id=wallet,
        category_id=expense.id,
        legs=(
            TransactionLeg(currency_id=display.id, amount=Decimal("1")),
            TransactionLeg(currency_id=source.id, amount=Decimal("3")),
        ),
    )
    for _ in range(3):
        await env.add_transaction(
            workspace_id, wallet_id=wallet, category_id=income.id, currency_id=source.id, amount=Decimal("1")
        )

    buckets, _ = await env.service.get_analytics(
        workspace_id,
        display_currency_id=display.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    [(_, income_sum, _)] = buckets
    # Каждая операция: 1 * (1/3) = 0.333... Сумма трёх неокруглённых = 1.0 ровно -> округление даёт 1.00.
    # Если бы округляли каждую операцию отдельно (0.33 * 3 = 0.99), результат был бы иным.
    assert income_sum == Decimal("1.00")


async def test_income_and_expense_both_present_when_type_filter_applied() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount=Decimal("100")
    )

    buckets, _ = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=CategoryType.INCOME,
    )

    [(_, income_sum, expense_sum)] = buckets
    assert income_sum == Decimal("100")
    assert expense_sum == Decimal("0")


async def test_empty_buckets_not_included() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert buckets == []
    assert unconverted == []


async def test_service_does_not_depend_on_transfer_repository() -> None:
    env = Environment()
    workspace_id = uuid4()
    currency = await env.make_currency()
    wallet = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    await env.add_transaction(
        workspace_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount=Decimal("100")
    )

    # AnalyticsService сконструирован без ссылки на TransferRepository (сигнатура __init__ принимает
    # только TransactionRepository и CurrencyRepository) — переводы структурно не могут повлиять на расчёт.
    buckets, _ = await env.service.get_analytics(
        workspace_id,
        display_currency_id=currency.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    [(_, income_sum, _)] = buckets
    assert income_sum == Decimal("100")


async def test_date_from_after_date_to_raises_client_error() -> None:
    env = Environment()
    currency = await env.make_currency()

    with pytest.raises(ClientError):
        await env.service.get_analytics(
            uuid4(),
            display_currency_id=currency.id,
            date_from=DATE_TO,
            date_to=DATE_FROM,
            group_by="wallet",
            wallet_id=None,
            category_id=None,
            currency_id=None,
            type=None,
        )


async def test_unknown_display_currency_raises_client_error() -> None:
    env = Environment()

    with pytest.raises(ClientError):
        await env.service.get_analytics(
            uuid4(),
            display_currency_id=uuid4(),
            date_from=DATE_FROM,
            date_to=DATE_TO,
            group_by="wallet",
            wallet_id=None,
            category_id=None,
            currency_id=None,
            type=None,
        )


async def test_filters_narrow_operations_but_not_rate_topups() -> None:
    env = Environment()
    workspace_id = uuid4()
    display = await env.make_currency("RUB")
    source = await env.make_currency("CNY")
    wallet_filtered = uuid4()
    wallet_other = uuid4()
    income = await env.make_category(workspace_id, CategoryType.INCOME)
    # Пополнение (для курса) относится к другому кошельку, не входящему в фильтр запроса.
    await env.add_topup(
        workspace_id,
        wallet_id=wallet_other,
        category_id=income.id,
        legs=(
            TransactionLeg(currency_id=display.id, amount=Decimal("10")),
            TransactionLeg(currency_id=source.id, amount=Decimal("100")),
        ),
    )
    await env.add_transaction(
        workspace_id, wallet_id=wallet_filtered, category_id=income.id, currency_id=source.id, amount=Decimal("100")
    )

    buckets, unconverted = await env.service.get_analytics(
        workspace_id,
        display_currency_id=display.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=wallet_filtered,
        category_id=None,
        currency_id=None,
        type=None,
    )

    assert unconverted == []
    [(key, income_sum, _)] = buckets
    assert key == wallet_filtered
    # Курс 10/100 = 0.1, применён к операции отфильтрованного кошелька, хотя пополнение относится к другому.
    assert income_sum == Decimal("10")


async def test_owner_isolation_excludes_foreign_operations_and_topups() -> None:
    env = Environment()
    user_a = uuid4()
    user_b = uuid4()
    display = await env.make_currency("RUB")
    source = await env.make_currency("CNY")
    wallet = uuid4()
    income_a = await env.make_category(user_a, CategoryType.INCOME)
    income_b = await env.make_category(user_b, CategoryType.INCOME)
    # Чужая операция.
    await env.add_transaction(
        user_b, wallet_id=wallet, category_id=income_b.id, currency_id=display.id, amount=Decimal("999")
    )
    # Чужое пополнение с курсом для source -> display, не должно применяться к пользователю A.
    await env.add_topup(
        user_b,
        wallet_id=wallet,
        category_id=income_b.id,
        legs=(
            TransactionLeg(currency_id=display.id, amount=Decimal("10")),
            TransactionLeg(currency_id=source.id, amount=Decimal("100")),
        ),
    )
    await env.add_transaction(
        user_a, wallet_id=wallet, category_id=income_a.id, currency_id=source.id, amount=Decimal("50")
    )

    buckets, unconverted = await env.service.get_analytics(
        user_a,
        display_currency_id=display.id,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        group_by="wallet",
        wallet_id=None,
        category_id=None,
        currency_id=None,
        type=None,
    )

    # Курса нет (чужое пополнение не в счёт) -> сумма пользователя A по source исключена, валюта неконвертируема.
    assert buckets == []
    assert unconverted == [source.id]
