from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Wallet, Workspace
from core.exceptions import ClientError, NotFoundError
from core.services.topup import TopupService
from core.services.topup_legs import CrossCurrencyTopupLegs, SameCurrencyTopupLegs
from tests.fakes import (
    FixedClock,
    InMemoryCategoryRepository,
    InMemoryCurrencyRepository,
    InMemoryTransactionRepository,
    InMemoryWalletRepository,
    InMemoryWorkspaceRepository,
    SequentialIdGenerator,
)


class Environment:
    def __init__(self) -> None:
        self.categories = InMemoryCategoryRepository()
        self.transactions = InMemoryTransactionRepository(self.categories)
        self.wallets = InMemoryWalletRepository()
        self.currencies = InMemoryCurrencyRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.clock = FixedClock()
        self.service = TopupService(
            self.transactions,
            self.wallets,
            self.categories,
            self.currencies,
            self.workspaces,
            (SameCurrencyTopupLegs(), CrossCurrencyTopupLegs()),
            self.clock,
            SequentialIdGenerator(),
        )

    async def currency(self, code: str, decimal_places: int = 2) -> Currency:
        currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
        await self.currencies.upsert_many([currency])
        return currency

    async def workspace(self, currency: Currency) -> UUID:
        workspace = Workspace(
            id=uuid4(),
            user_id=uuid4(),
            name="Воркспейс",
            currency_id=currency.id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        await self.workspaces.add(workspace)
        return workspace.id

    async def wallet(self, workspace_id: UUID, currency: Currency) -> Wallet:
        return await self.wallets.add(
            Wallet(
                id=uuid4(),
                workspace_id=workspace_id,
                name="Кошелёк",
                icon="wallet",
                currency_id=currency.id,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    async def category(self, workspace_id: UUID, type: CategoryType = CategoryType.INCOME) -> Category:
        return await self.categories.add(
            Category(
                id=uuid4(),
                workspace_id=workspace_id,
                type=type,
                name=f"Категория {uuid4()}",
                icon="wallet",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )


def leg(currency: Currency, amount: str) -> TransactionLeg:
    return TransactionLeg(currency_id=currency.id, amount=Decimal(amount))


async def test_create_topup_with_single_leg_when_currencies_match() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)

    topup = await env.service.create_topup(
        workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "100")], occurred_at=None
    )

    assert topup.legs == (leg(cny, "100"),)
    assert topup.occurred_at == env.clock.now()


async def test_create_topup_with_two_legs_when_currencies_differ() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    rub = await env.currency("RUB")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, rub)
    category = await env.category(workspace_id)

    topup = await env.service.create_topup(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        legs=[leg(cny, "780"), leg(rub, "10000")],
        occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        comment="Обмен",
    )

    assert {item.currency_id for item in topup.legs} == {cny.id, rub.id}
    assert topup.occurred_at == datetime(2026, 3, 1, tzinfo=UTC)
    assert topup.comment == "Обмен"


@pytest.mark.parametrize(
    ("workspace_code", "wallet_code", "leg_codes"),
    [
        ("CNY", "RUB", ["RUB"]),
        ("CNY", "RUB", ["CNY"]),
        ("CNY", "CNY", ["CNY", "RUB"]),
        ("CNY", "RUB", ["CNY", "USDT"]),
        ("CNY", "RUB", ["CNY", "RUB", "USDT"]),
        ("CNY", "RUB", []),
    ],
)
async def test_create_topup_rejects_wrong_currency_set(
    workspace_code: str, wallet_code: str, leg_codes: list[str]
) -> None:
    env = Environment()
    currencies = {code: await env.currency(code) for code in {"CNY", "RUB", "USDT"}}
    workspace_id = await env.workspace(currencies[workspace_code])
    wallet = await env.wallet(workspace_id, currencies[wallet_code])
    category = await env.category(workspace_id)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=[leg(currencies[code], "1") for code in leg_codes],
            occurred_at=None,
        )


async def test_create_topup_error_lists_missing_and_extra_currency_codes() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    rub = await env.currency("RUB")
    usdt = await env.currency("USDT")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, rub)
    category = await env.category(workspace_id)

    with pytest.raises(ClientError) as error:
        await env.service.create_topup(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=[leg(cny, "1"), leg(usdt, "1")],
            occurred_at=None,
        )

    assert "RUB" in str(error.value)
    assert "USDT" in str(error.value)


async def test_create_topup_rejects_duplicate_currency() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=[leg(cny, "1"), leg(cny, "2")],
            occurred_at=None,
        )


async def test_create_topup_rejects_expense_category() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id, CategoryType.EXPENSE)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
        )


@pytest.mark.parametrize("amount", ["0", "-1", "1.001"])
async def test_create_topup_rejects_invalid_amount(amount: str) -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)

    with pytest.raises(ClientError):
        await env.service.create_topup(
            workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, amount)], occurred_at=None
        )


async def test_create_topup_checks_precision_per_leg_currency() -> None:
    env = Environment()
    cny = await env.currency("CNY", decimal_places=2)
    usdt = await env.currency("USDT", decimal_places=6)
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, usdt)
    category = await env.category(workspace_id)

    topup = await env.service.create_topup(
        workspace_id,
        wallet_id=wallet.id,
        category_id=category.id,
        legs=[leg(cny, "100.50"), leg(usdt, "13.123456")],
        occurred_at=None,
    )
    assert len(topup.legs) == 2

    with pytest.raises(ClientError):
        await env.service.create_topup(
            workspace_id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=[leg(cny, "100.505"), leg(usdt, "13")],
            occurred_at=None,
        )


async def test_create_topup_rejects_foreign_wallet_and_category() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    other_workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)
    foreign_wallet = await env.wallet(other_workspace_id, cny)
    foreign_category = await env.category(other_workspace_id)

    with pytest.raises(NotFoundError):
        await env.service.create_topup(
            workspace_id, wallet_id=foreign_wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
        )
    with pytest.raises(NotFoundError):
        await env.service.create_topup(
            workspace_id, wallet_id=wallet.id, category_id=foreign_category.id, legs=[leg(cny, "1")], occurred_at=None
        )


async def test_create_topup_rejects_unknown_workspace() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = uuid4()
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)

    with pytest.raises(NotFoundError):
        await env.service.create_topup(
            workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
        )


async def test_get_topup_returns_topup_and_hides_expense_and_foreign() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    income = await env.category(workspace_id)
    expense_category = await env.category(workspace_id, CategoryType.EXPENSE)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=wallet.id, category_id=income.id, legs=[leg(cny, "1")], occurred_at=None
    )
    expense = await env.transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            category_id=expense_category.id,
            legs=(leg(cny, "1"),),
            occurred_at=env.clock.now(),
            created_at=env.clock.now(),
        )
    )

    assert (await env.service.get_topup(topup.id, workspace_id)).id == topup.id
    with pytest.raises(NotFoundError):
        await env.service.get_topup(expense.id, workspace_id)
    with pytest.raises(NotFoundError):
        await env.service.get_topup(topup.id, uuid4())


async def test_list_topups_returns_only_topups_of_workspace() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    other_workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    other_wallet = await env.wallet(other_workspace_id, cny)
    income = await env.category(workspace_id)
    other_income = await env.category(other_workspace_id)
    expense_category = await env.category(workspace_id, CategoryType.EXPENSE)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=wallet.id, category_id=income.id, legs=[leg(cny, "1")], occurred_at=None
    )
    await env.service.create_topup(
        other_workspace_id,
        wallet_id=other_wallet.id,
        category_id=other_income.id,
        legs=[leg(cny, "1")],
        occurred_at=None,
    )
    await env.transactions.add(
        Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            category_id=expense_category.id,
            legs=(leg(cny, "1"),),
            occurred_at=env.clock.now(),
            created_at=env.clock.now(),
        )
    )

    items, total = await env.service.list_topups(
        workspace_id, wallet_id=None, category_id=None, date_from=None, date_to=None, limit=20, offset=0
    )

    assert total == 1
    assert [item.id for item in items] == [topup.id]


async def test_list_topups_rejects_inverted_date_range() -> None:
    env = Environment()

    with pytest.raises(ClientError):
        await env.service.list_topups(
            uuid4(),
            wallet_id=None,
            category_id=None,
            date_from=datetime(2026, 2, 1, tzinfo=UTC),
            date_to=datetime(2026, 1, 1, tzinfo=UTC),
            limit=20,
            offset=0,
        )


async def test_update_topup_replaces_legs_and_fields() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    rub = await env.currency("RUB")
    workspace_id = await env.workspace(cny)
    cny_wallet = await env.wallet(workspace_id, cny)
    rub_wallet = await env.wallet(workspace_id, rub)
    category = await env.category(workspace_id)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=cny_wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
    )

    updated = await env.service.update_topup(
        topup.id,
        workspace_id,
        wallet_id=rub_wallet.id,
        category_id=category.id,
        legs=[leg(cny, "780"), leg(rub, "10000")],
        occurred_at=None,
        comment="Новый",
    )

    assert updated.wallet_id == rub_wallet.id
    assert {item.currency_id for item in updated.legs} == {cny.id, rub.id}
    assert updated.comment == "Новый"
    assert updated.updated_at == env.clock.now()


async def test_update_topup_applies_leg_rule_for_new_wallet() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    rub = await env.currency("RUB")
    workspace_id = await env.workspace(cny)
    cny_wallet = await env.wallet(workspace_id, cny)
    rub_wallet = await env.wallet(workspace_id, rub)
    category = await env.category(workspace_id)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=cny_wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
    )

    with pytest.raises(ClientError):
        await env.service.update_topup(
            topup.id,
            workspace_id,
            wallet_id=rub_wallet.id,
            category_id=category.id,
            legs=[leg(cny, "1")],
            occurred_at=None,
        )
    assert (await env.service.get_topup(topup.id, workspace_id)).wallet_id == cny_wallet.id


async def test_update_unknown_topup_raises_not_found() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)

    with pytest.raises(NotFoundError):
        await env.service.update_topup(
            uuid4(), workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
        )


async def test_delete_topup_removes_it() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
    )

    await env.service.delete_topup(topup.id, workspace_id)

    with pytest.raises(NotFoundError):
        await env.service.get_topup(topup.id, workspace_id)


async def test_delete_unknown_or_foreign_topup_raises_not_found() -> None:
    env = Environment()
    cny = await env.currency("CNY")
    workspace_id = await env.workspace(cny)
    wallet = await env.wallet(workspace_id, cny)
    category = await env.category(workspace_id)
    topup = await env.service.create_topup(
        workspace_id, wallet_id=wallet.id, category_id=category.id, legs=[leg(cny, "1")], occurred_at=None
    )

    with pytest.raises(NotFoundError):
        await env.service.delete_topup(uuid4(), workspace_id)
    with pytest.raises(NotFoundError):
        await env.service.delete_topup(topup.id, uuid4())
