from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg
from depends.auth import get_current_user
from depends.currency import get_currency_repository
from depends.transaction import get_transaction_repository
from main import create_app
from tests.fakes import InMemoryCategoryRepository, InMemoryCurrencyRepository, InMemoryTransactionRepository

DATE_FROM = "2026-01-01T00:00:00Z"
DATE_TO = "2026-01-31T00:00:00Z"
IN_RANGE = datetime(2026, 1, 15, tzinfo=UTC)


def make_client(
    *,
    categories: InMemoryCategoryRepository | None = None,
    currencies: InMemoryCurrencyRepository | None = None,
    transactions: InMemoryTransactionRepository | None = None,
    user_id: UUID | None = None,
    authenticated: bool = True,
) -> TestClient:
    categories = categories if categories is not None else InMemoryCategoryRepository()
    currencies = currencies if currencies is not None else InMemoryCurrencyRepository()
    transactions = transactions if transactions is not None else InMemoryTransactionRepository(categories)
    user_id = user_id if user_id is not None else uuid4()
    app = create_app()
    app.dependency_overrides[get_currency_repository] = lambda: currencies
    app.dependency_overrides[get_transaction_repository] = lambda: transactions
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app)


async def make_currency(
    currencies: InMemoryCurrencyRepository, code: str = "RUB", decimal_places: int = 2
) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await currencies.upsert_many([currency])
    return currency


async def make_category(
    categories: InMemoryCategoryRepository, user_id: UUID, type: CategoryType = CategoryType.INCOME
) -> Category:
    category = Category(
        id=uuid4(), user_id=user_id, type=type, name=f"Категория {uuid4()}", icon="wallet", created_at=IN_RANGE
    )
    return await categories.add(category)


async def add_transaction(
    transactions: InMemoryTransactionRepository,
    user_id: UUID,
    *,
    wallet_id: UUID,
    category_id: UUID,
    currency_id: UUID,
    amount: str,
) -> None:
    await transactions.add(
        Transaction(
            id=uuid4(),
            user_id=user_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=(TransactionLeg(currency_id=currency_id, amount=Decimal(amount)),),
            occurred_at=IN_RANGE,
            created_at=IN_RANGE,
        )
    )


async def add_topup(
    transactions: InMemoryTransactionRepository,
    user_id: UUID,
    *,
    wallet_id: UUID,
    category_id: UUID,
    legs: list[tuple[UUID, str]],
) -> None:
    await transactions.add(
        Transaction(
            id=uuid4(),
            user_id=user_id,
            wallet_id=wallet_id,
            category_id=category_id,
            legs=tuple(
                TransactionLeg(currency_id=currency_id, amount=Decimal(amount)) for currency_id, amount in legs
            ),
            occurred_at=IN_RANGE,
            created_at=IN_RANGE,
        )
    )


def base_query(*, display_currency: UUID, group_by: str = "wallet") -> dict:
    return {
        "display_currency": str(display_currency),
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "group_by": group_by,
    }


async def test_group_by_wallet_returns_200_with_buckets() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency = await make_currency(currencies)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    wallet_a, wallet_b = uuid4(), uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet_a, category_id=income.id, currency_id=currency.id, amount="100"
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet_b, category_id=income.id, currency_id=currency.id, amount="50"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=currency.id, group_by="wallet"))

    assert response.status_code == 200
    body = response.json()
    assert body["display_currency_id"] == str(currency.id)
    keys = {bucket["group_key"] for bucket in body["buckets"]}
    assert keys == {str(wallet_a), str(wallet_b)}


async def test_group_by_category_returns_200_with_buckets() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency = await make_currency(currencies)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    wallet = uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount="100"
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=expense.id, currency_id=currency.id, amount="30"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=currency.id, group_by="category"))

    assert response.status_code == 200
    by_key = {bucket["group_key"]: bucket for bucket in response.json()["buckets"]}
    assert by_key[str(income.id)]["income"] == "100.00"
    assert by_key[str(expense.id)]["expense"] == "30.00"


async def test_group_by_currency_returns_200_with_buckets() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    income = await make_category(categories, user_id, CategoryType.INCOME)
    wallet = uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=rub.id, amount="100"
    )
    await add_topup(
        transactions,
        user_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=[(rub.id, "10000"), (cny.id, "780")],
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=rub.id, group_by="currency"))

    assert response.status_code == 200
    keys = {bucket["group_key"] for bucket in response.json()["buckets"]}
    assert keys == {str(rub.id), str(cny.id)}


async def test_conversion_reproducible_example() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency_a = await make_currency(currencies, "A")
    currency_b = await make_currency(currencies, "B", decimal_places=8)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    wallet = uuid4()
    await add_topup(
        transactions,
        user_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=[(currency_a.id, "10000"), (currency_b.id, "780")],
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=expense.id, currency_id=currency_a.id, amount="1000"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=currency_b.id, group_by="wallet"))

    assert response.status_code == 200
    [bucket] = response.json()["buckets"]
    assert bucket["expense"] == "78.00000000"


async def test_unconverted_currency_does_not_fail_whole_request() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    display = await make_currency(currencies, "RUB")
    convertible = await make_currency(currencies, "CNY")
    unconvertible = await make_currency(currencies, "USD")
    income = await make_category(categories, user_id, CategoryType.INCOME)
    wallet = uuid4()
    await add_topup(
        transactions,
        user_id,
        wallet_id=wallet,
        category_id=income.id,
        legs=[(display.id, "100"), (convertible.id, "10")],
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=unconvertible.id, amount="5"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=display.id, group_by="currency"))

    assert response.status_code == 200
    body = response.json()
    assert body["unconverted_currencies"] == [str(unconvertible.id)]
    keys = {bucket["group_key"] for bucket in body["buckets"]}
    assert str(unconvertible.id) not in keys
    assert str(display.id) in keys
    assert str(convertible.id) in keys


async def test_rounding_of_bucket_total() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    display = await make_currency(currencies, "RUB", decimal_places=2)
    source = await make_currency(currencies, "CNY")
    income = await make_category(categories, user_id, CategoryType.INCOME)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    wallet = uuid4()
    await add_topup(
        transactions, user_id, wallet_id=wallet, category_id=expense.id, legs=[(display.id, "1"), (source.id, "3")]
    )
    for _ in range(3):
        await add_transaction(
            transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=source.id, amount="1"
        )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get("/api/analytics", params=base_query(display_currency=display.id, group_by="wallet"))

    assert response.status_code == 200
    [bucket] = response.json()["buckets"]
    assert bucket["income"] == "1.00"


async def test_missing_date_from_rejected() -> None:
    currencies = InMemoryCurrencyRepository()
    currency_id = uuid4()
    client = make_client(currencies=currencies)

    response = client.get(
        "/api/analytics",
        params={"display_currency": str(currency_id), "date_to": DATE_TO, "group_by": "wallet"},
    )

    assert response.status_code == 400


async def test_missing_date_to_rejected() -> None:
    currencies = InMemoryCurrencyRepository()
    currency_id = uuid4()
    client = make_client(currencies=currencies)

    response = client.get(
        "/api/analytics",
        params={"display_currency": str(currency_id), "date_from": DATE_FROM, "group_by": "wallet"},
    )

    assert response.status_code == 400


async def test_date_from_after_date_to_rejected() -> None:
    currencies = InMemoryCurrencyRepository()
    currency = await make_currency(currencies)
    client = make_client(currencies=currencies)

    response = client.get(
        "/api/analytics",
        params={
            "display_currency": str(currency.id),
            "date_from": DATE_TO,
            "date_to": DATE_FROM,
            "group_by": "wallet",
        },
    )

    assert response.status_code == 400


async def test_unknown_display_currency_rejected() -> None:
    client = make_client()

    response = client.get("/api/analytics", params=base_query(display_currency=uuid4()))

    assert response.status_code == 400


async def test_missing_display_currency_rejected() -> None:
    client = make_client()

    response = client.get("/api/analytics", params={"date_from": DATE_FROM, "date_to": DATE_TO, "group_by": "wallet"})

    assert response.status_code == 400


async def test_filter_by_wallet() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency = await make_currency(currencies)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    wallet_a, wallet_b = uuid4(), uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet_a, category_id=income.id, currency_id=currency.id, amount="100"
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet_b, category_id=income.id, currency_id=currency.id, amount="50"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get(
        "/api/analytics",
        params={**base_query(display_currency=currency.id, group_by="wallet"), "wallet_id": str(wallet_a)},
    )

    assert response.status_code == 200
    [bucket] = response.json()["buckets"]
    assert bucket["group_key"] == str(wallet_a)


async def test_filter_by_category() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency = await make_currency(currencies)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    wallet = uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount="100"
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=expense.id, currency_id=currency.id, amount="30"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get(
        "/api/analytics",
        params={**base_query(display_currency=currency.id, group_by="category"), "category_id": str(income.id)},
    )

    assert response.status_code == 200
    [bucket] = response.json()["buckets"]
    assert bucket["group_key"] == str(income.id)


async def test_filter_by_currency() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    rub = await make_currency(currencies, "RUB")
    cny = await make_currency(currencies, "CNY")
    income = await make_category(categories, user_id, CategoryType.INCOME)
    wallet = uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=rub.id, amount="100"
    )
    await add_topup(
        transactions, user_id, wallet_id=wallet, category_id=income.id, legs=[(rub.id, "100"), (cny.id, "10")]
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get(
        "/api/analytics",
        params={**base_query(display_currency=rub.id, group_by="currency"), "currency_id": str(cny.id)},
    )

    assert response.status_code == 200
    keys = {bucket["group_key"] for bucket in response.json()["buckets"]}
    assert keys == {str(cny.id)}


async def test_filter_by_type() -> None:
    user_id = uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    currency = await make_currency(currencies)
    income = await make_category(categories, user_id, CategoryType.INCOME)
    expense = await make_category(categories, user_id, CategoryType.EXPENSE)
    wallet = uuid4()
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=income.id, currency_id=currency.id, amount="100"
    )
    await add_transaction(
        transactions, user_id, wallet_id=wallet, category_id=expense.id, currency_id=currency.id, amount="30"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_id)

    response = client.get(
        "/api/analytics",
        params={**base_query(display_currency=currency.id, group_by="wallet"), "type": "income"},
    )

    assert response.status_code == 200
    [bucket] = response.json()["buckets"]
    assert bucket["income"] == "100.00"
    assert bucket["expense"] == "0.00"


async def test_unauthenticated_request_rejected() -> None:
    client = make_client(authenticated=False)

    response = client.get("/api/analytics", params=base_query(display_currency=uuid4()))

    assert response.status_code == 401


async def test_owner_isolation_excludes_foreign_data() -> None:
    user_a, user_b = uuid4(), uuid4()
    categories = InMemoryCategoryRepository()
    currencies = InMemoryCurrencyRepository()
    transactions = InMemoryTransactionRepository(categories)
    display = await make_currency(currencies, "RUB")
    source = await make_currency(currencies, "CNY")
    income_a = await make_category(categories, user_a, CategoryType.INCOME)
    income_b = await make_category(categories, user_b, CategoryType.INCOME)
    wallet = uuid4()
    await add_transaction(
        transactions, user_b, wallet_id=wallet, category_id=income_b.id, currency_id=display.id, amount="999"
    )
    await add_topup(
        transactions, user_b, wallet_id=wallet, category_id=income_b.id, legs=[(display.id, "10"), (source.id, "100")]
    )
    await add_transaction(
        transactions, user_a, wallet_id=wallet, category_id=income_a.id, currency_id=source.id, amount="50"
    )
    client = make_client(categories=categories, currencies=currencies, transactions=transactions, user_id=user_a)

    response = client.get("/api/analytics", params=base_query(display_currency=display.id, group_by="wallet"))

    assert response.status_code == 200
    body = response.json()
    # Чужое пополнение (курс) не в счёт — валюта пользователя A неконвертируема, чужая операция не в суммах.
    assert body["buckets"] == []
    assert body["unconverted_currencies"] == [str(source.id)]
