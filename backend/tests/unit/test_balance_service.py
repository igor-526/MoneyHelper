from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Wallet
from core.exceptions import NotFoundError
from core.services.balance import BalanceService
from tests.fakes import InMemoryWalletRepository


class StubContributor:
    def __init__(self, deltas: dict[tuple[UUID, UUID], dict[UUID, Decimal]]) -> None:
        self._deltas = deltas

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID) -> dict[UUID, Decimal]:
        return self._deltas.get((wallet_id, workspace_id), {})


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id: UUID, currency_ids: list[UUID]) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=tuple(currency_ids),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def test_get_wallet_balances_zero_with_single_contributor_without_activity() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, [currency])
    service = BalanceService(wallets, [StubContributor({})])

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(currency, Decimal("0"))]


async def test_get_wallet_balances_single_contributor_computes_delta() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, [currency])
    contributor = StubContributor({(wallet.id, owner): {currency: Decimal("70")}})
    service = BalanceService(wallets, [contributor])

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(currency, Decimal("70"))]


async def test_get_wallet_balances_sums_multiple_contributors_per_currency() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, [currency])
    contributor_a = StubContributor({(wallet.id, owner): {currency: Decimal("100")}})
    contributor_b = StubContributor({(wallet.id, owner): {currency: Decimal("-30")}})
    service = BalanceService(wallets, [contributor_a, contributor_b])

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(currency, Decimal("70"))]


async def test_get_wallet_balances_separates_currencies_across_contributors() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    rub, cny = uuid4(), uuid4()
    wallet = await make_wallet(wallets, owner, [rub, cny])
    contributor_a = StubContributor({(wallet.id, owner): {rub: Decimal("100")}})
    contributor_b = StubContributor({(wallet.id, owner): {cny: Decimal("50")}})
    service = BalanceService(wallets, [contributor_a, contributor_b])

    balances = await service.get_wallet_balances(wallet.id, owner)

    assert balances == [(rub, Decimal("100")), (cny, Decimal("50"))]


async def test_get_wallet_balances_unknown_wallet_raises_not_found() -> None:
    wallets = InMemoryWalletRepository()
    service = BalanceService(wallets, [StubContributor({})])

    with pytest.raises(NotFoundError):
        await service.get_wallet_balances(uuid4(), uuid4())


async def test_get_wallet_balances_foreign_wallet_raises_not_found() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    wallet = await make_wallet(wallets, owner, [uuid4()])
    service = BalanceService(wallets, [StubContributor({})])

    with pytest.raises(NotFoundError):
        await service.get_wallet_balances(wallet.id, uuid4())
