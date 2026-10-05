from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.entities import Wallet
from core.exceptions import NotFoundError
from core.services.balance import BalanceService
from tests.fakes import InMemoryWalletRepository


class StubContributor:
    def __init__(self, deltas: dict[tuple[UUID, UUID, UUID], Decimal]) -> None:
        self._deltas = deltas

    async def balance_delta(self, wallet_id: UUID, workspace_id: UUID, currency_id: UUID) -> Decimal:
        return self._deltas.get((wallet_id, workspace_id, currency_id), Decimal("0"))


async def make_wallet(wallets: InMemoryWalletRepository, workspace_id: UUID, currency_id: UUID) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_id=currency_id,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return await wallets.add(wallet)


async def test_get_wallet_balance_zero_with_single_contributor_without_activity() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, currency)
    service = BalanceService(wallets, [StubContributor({})])

    balance = await service.get_wallet_balance(wallet.id, owner)

    assert balance == (currency, Decimal("0"))


async def test_get_wallet_balance_single_contributor_computes_delta() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, currency)
    contributor = StubContributor({(wallet.id, owner, currency): Decimal("70")})
    service = BalanceService(wallets, [contributor])

    balance = await service.get_wallet_balance(wallet.id, owner)

    assert balance == (currency, Decimal("70"))


async def test_get_wallet_balance_sums_multiple_contributors() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    currency = uuid4()
    wallet = await make_wallet(wallets, owner, currency)
    contributor_a = StubContributor({(wallet.id, owner, currency): Decimal("100")})
    contributor_b = StubContributor({(wallet.id, owner, currency): Decimal("-30")})
    service = BalanceService(wallets, [contributor_a, contributor_b])

    balance = await service.get_wallet_balance(wallet.id, owner)

    assert balance == (currency, Decimal("70"))


async def test_get_wallet_balance_requests_deltas_in_wallet_currency_only() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    wallet_currency, other_currency = uuid4(), uuid4()
    wallet = await make_wallet(wallets, owner, wallet_currency)
    contributor = StubContributor(
        {(wallet.id, owner, wallet_currency): Decimal("100"), (wallet.id, owner, other_currency): Decimal("999")}
    )
    service = BalanceService(wallets, [contributor])

    balance = await service.get_wallet_balance(wallet.id, owner)

    assert balance == (wallet_currency, Decimal("100"))


async def test_get_wallet_balance_unknown_wallet_raises_not_found() -> None:
    wallets = InMemoryWalletRepository()
    service = BalanceService(wallets, [StubContributor({})])

    with pytest.raises(NotFoundError):
        await service.get_wallet_balance(uuid4(), uuid4())


async def test_get_wallet_balance_foreign_wallet_raises_not_found() -> None:
    wallets = InMemoryWalletRepository()
    owner = uuid4()
    wallet = await make_wallet(wallets, owner, uuid4())
    service = BalanceService(wallets, [StubContributor({})])

    with pytest.raises(NotFoundError):
        await service.get_wallet_balance(wallet.id, uuid4())
