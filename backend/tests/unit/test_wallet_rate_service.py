from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Transaction, TransactionLeg, Wallet
from core.exceptions import ClientError, NotFoundError
from core.services.wallet_rate import WalletRateService
from tests.fakes import InMemoryCategoryRepository, InMemoryTransactionRepository, InMemoryWalletRepository

OCCURRED_AT = datetime(2026, 1, 15, tzinfo=UTC)


class Environment:
    def __init__(self) -> None:
        self.wallets = InMemoryWalletRepository()
        self.transactions = InMemoryTransactionRepository(InMemoryCategoryRepository())
        self.service = WalletRateService(self.transactions, self.wallets)

    async def make_wallet(self, workspace_id: UUID, currency_ids: tuple[UUID, ...]) -> Wallet:
        wallet = Wallet(
            id=uuid4(),
            workspace_id=workspace_id,
            name="Alipay",
            icon="wallet",
            currency_ids=currency_ids,
            created_at=OCCURRED_AT,
        )
        return await self.wallets.add(wallet)

    async def add_topup(self, workspace_id: UUID, wallet_id: UUID, legs: dict[UUID, Decimal]) -> Transaction:
        transaction = Transaction(
            id=uuid4(),
            workspace_id=workspace_id,
            wallet_id=wallet_id,
            category_id=uuid4(),
            legs=tuple(TransactionLeg(currency_id=cid, amount=amount) for cid, amount in legs.items()),
            occurred_at=OCCURRED_AT,
            created_at=OCCURRED_AT,
        )
        return await self.transactions.add(transaction)


async def test_averages_rate_from_wallet_topups() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id, cny_id = uuid4(), uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id, cny_id))
    await env.add_topup(workspace_id, wallet.id, {rub_id: Decimal("10000"), cny_id: Decimal("780")})
    await env.add_topup(workspace_id, wallet.id, {rub_id: Decimal("5000"), cny_id: Decimal("400")})

    result = await env.service.get_wallet_rates(wallet.id, workspace_id, target_currency_id=rub_id)

    expected = ((Decimal("10000") / Decimal("780")) + (Decimal("5000") / Decimal("400"))) / 2
    assert result.target_currency_id == rub_id
    assert result.rates[cny_id] == expected.quantize(Decimal("1.0000000000"))
    assert result.unrated_currency_ids == []


async def test_currency_without_topups_is_unrated() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id, cny_id, usdt_id = uuid4(), uuid4(), uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id, cny_id, usdt_id))
    await env.add_topup(workspace_id, wallet.id, {rub_id: Decimal("10000"), cny_id: Decimal("780")})

    result = await env.service.get_wallet_rates(wallet.id, workspace_id, target_currency_id=rub_id)

    assert cny_id in result.rates
    assert result.unrated_currency_ids == [usdt_id]


async def test_single_currency_wallet_returns_empty_result() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id = uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id,))

    result = await env.service.get_wallet_rates(wallet.id, workspace_id, target_currency_id=rub_id)

    assert result.rates == {}
    assert result.unrated_currency_ids == []


async def test_topups_of_other_wallet_are_ignored() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id, cny_id = uuid4(), uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id, cny_id))
    other_wallet = await env.make_wallet(workspace_id, (rub_id, cny_id))
    await env.add_topup(workspace_id, other_wallet.id, {rub_id: Decimal("10000"), cny_id: Decimal("780")})

    result = await env.service.get_wallet_rates(wallet.id, workspace_id, target_currency_id=rub_id)

    assert result.rates == {}
    assert result.unrated_currency_ids == [cny_id]


async def test_unknown_target_currency_is_rejected() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id, cny_id, usdt_id = uuid4(), uuid4(), uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id, cny_id))

    with pytest.raises(ClientError):
        await env.service.get_wallet_rates(wallet.id, workspace_id, target_currency_id=usdt_id)


async def test_missing_wallet_is_not_found() -> None:
    env = Environment()

    with pytest.raises(NotFoundError):
        await env.service.get_wallet_rates(uuid4(), uuid4(), target_currency_id=uuid4())


async def test_wallet_of_another_workspace_is_not_found() -> None:
    env = Environment()
    workspace_id = uuid4()
    rub_id = uuid4()
    wallet = await env.make_wallet(workspace_id, (rub_id,))

    with pytest.raises(NotFoundError):
        await env.service.get_wallet_rates(wallet.id, uuid4(), target_currency_id=rub_id)
