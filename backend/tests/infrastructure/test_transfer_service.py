from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ClientError
from core.services.balance import BalanceService
from core.services.transfer import TransferService
from repositories.currency import CurrencyRepository
from repositories.transfer import TransferRepository
from repositories.wallet import WalletRepository
from tests.fakes import FixedClock, SequentialIdGenerator
from tests.infrastructure.test_transfer_repository import make_currency, make_wallet, make_workspace

pytestmark = pytest.mark.infrastructure


def make_services(db_session: AsyncSession) -> tuple[TransferService, BalanceService]:
    transfers = TransferRepository(db_session)
    wallets = WalletRepository(db_session)
    service = TransferService(
        transfers, wallets, CurrencyRepository(db_session), FixedClock(), SequentialIdGenerator()
    )
    return service, BalanceService(wallets, [transfers])


async def test_transfer_between_same_currency_wallets_moves_balance(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    currency = await make_currency(db_session)
    from_wallet = await make_wallet(db_session, workspace.id, currency.id)
    to_wallet = await make_wallet(db_session, workspace.id, currency.id)
    service, balances = make_services(db_session)

    await service.create_transfer(
        workspace.id,
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        amount=Decimal("40.00"),
        occurred_at=None,
    )

    assert await balances.get_wallet_balance(from_wallet.id, workspace.id) == (currency.id, Decimal("-40.00"))
    assert await balances.get_wallet_balance(to_wallet.id, workspace.id) == (currency.id, Decimal("40.00"))


async def test_transfer_between_different_currency_wallets_is_rejected(db_session: AsyncSession) -> None:
    workspace = await make_workspace(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    from_wallet = await make_wallet(db_session, workspace.id, rub.id)
    to_wallet = await make_wallet(db_session, workspace.id, cny.id)
    service, _ = make_services(db_session)

    with pytest.raises(ClientError, match="одной валюты"):
        await service.create_transfer(
            workspace.id,
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=Decimal("1.00"),
            occurred_at=None,
        )

    _, total = await service.list_transfers(
        workspace.id, wallet_id=None, date_from=None, date_to=None, limit=10, offset=0
    )
    assert total == 0
