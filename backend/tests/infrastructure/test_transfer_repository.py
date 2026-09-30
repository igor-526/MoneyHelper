from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Currency, Transfer, User, Wallet, Workspace
from models import currencies as currencies_table
from models import transfers as transfers_table
from models import wallets as wallets_table
from repositories.currency import CurrencyRepository
from repositories.transfer import TransferRepository
from repositories.user import UserRepository
from repositories.wallet import WalletRepository
from repositories.workspace import WorkspaceRepository

pytestmark = pytest.mark.infrastructure

DEFAULT_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


async def make_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        password_hash="hashed:password",
        token_version=0,
        created_at=DEFAULT_CREATED_AT,
    )
    await UserRepository(db_session).add(user)
    await db_session.flush()
    return user


async def make_workspace(db_session: AsyncSession, owner: User | None = None) -> Workspace:
    owner = owner if owner is not None else await make_user(db_session)
    workspace = Workspace(id=uuid4(), user_id=owner.id, name="Воркспейс", created_at=DEFAULT_CREATED_AT)
    await WorkspaceRepository(db_session).add(workspace)
    await db_session.flush()
    return workspace


async def make_currency(db_session: AsyncSession, code: str = "RUB", decimal_places: int = 2) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=decimal_places)
    await CurrencyRepository(db_session).upsert_many([currency])
    await db_session.flush()
    return currency


async def make_wallet(db_session: AsyncSession, workspace_id: UUID, currency_ids: tuple[UUID, ...]) -> Wallet:
    wallet = Wallet(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Кошелёк",
        icon="wallet",
        currency_ids=currency_ids,
        created_at=DEFAULT_CREATED_AT,
    )
    added = await WalletRepository(db_session).add(wallet)
    await db_session.flush()
    return added


def make_transfer(
    workspace_id: UUID,
    from_wallet_id: UUID,
    to_wallet_id: UUID,
    currency_id: UUID,
    *,
    amount: Decimal = Decimal("10.00"),
    occurred_at: datetime = DEFAULT_CREATED_AT,
) -> Transfer:
    return Transfer(
        id=uuid4(),
        workspace_id=workspace_id,
        from_wallet_id=from_wallet_id,
        to_wallet_id=to_wallet_id,
        currency_id=currency_id,
        amount=amount,
        occurred_at=occurred_at,
        created_at=DEFAULT_CREATED_AT,
    )


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id)

    added = await repo.add(transfer)
    await db_session.flush()

    assert added.amount == Decimal("10.00")
    fetched = await repo.get_by_id(transfer.id, user.id)
    assert fetched is not None
    assert fetched.from_wallet_id == wallet_a.id
    assert fetched.to_wallet_id == wallet_b.id
    assert fetched.currency_id == currency.id
    assert fetched.amount == Decimal("10.00")


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = TransferRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_get_by_id_with_foreign_workspace_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, owner.id, (currency.id,))
    wallet_b = await make_wallet(db_session, owner.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(owner.id, wallet_a.id, wallet_b.id, currency.id)
    await repo.add(transfer)
    await db_session.flush()

    assert await repo.get_by_id(transfer.id, other.id) is None


async def test_list_and_count_filter_by_wallet_matches_from_or_to(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    wallet_c = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    await repo.add(make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id))
    await repo.add(make_transfer(user.id, wallet_b.id, wallet_c.id, currency.id))
    await repo.add(make_transfer(user.id, wallet_c.id, wallet_a.id, currency.id))
    await db_session.flush()

    items = await repo.list(user.id, wallet_id=wallet_b.id, date_from=None, date_to=None, limit=20, offset=0)
    count = await repo.count(user.id, wallet_id=wallet_b.id, date_from=None, date_to=None)

    assert len(items) == 2
    assert count == 2
    assert {(item.from_wallet_id, item.to_wallet_id) for item in items} == {
        (wallet_a.id, wallet_b.id),
        (wallet_b.id, wallet_c.id),
    }


async def test_list_and_count_filter_by_date_range(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    early = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, occurred_at=datetime(2026, 1, 1, tzinfo=UTC))
    late = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, occurred_at=datetime(2026, 6, 1, tzinfo=UTC))
    await repo.add(early)
    await repo.add(late)
    await db_session.flush()

    items = await repo.list(
        user.id,
        wallet_id=None,
        date_from=datetime(2025, 12, 1, tzinfo=UTC),
        date_to=datetime(2026, 2, 1, tzinfo=UTC),
        limit=20,
        offset=0,
    )
    count = await repo.count(
        user.id, wallet_id=None, date_from=datetime(2025, 12, 1, tzinfo=UTC), date_to=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert [item.id for item in items] == [early.id]
    assert count == 1


async def test_list_is_sorted_by_occurred_at_desc_then_id_desc(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 2, 1, tzinfo=UTC)
    first = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, occurred_at=later)
    second = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, occurred_at=same_moment)
    third = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, occurred_at=same_moment)
    for transfer in (second, third, first):
        await repo.add(transfer)
    await db_session.flush()

    items = await repo.list(user.id, wallet_id=None, date_from=None, date_to=None, limit=20, offset=0)

    same_moment_ids_desc = sorted([second.id, third.id], reverse=True)
    assert [item.id for item in items] == [first.id, *same_moment_ids_desc]


async def test_list_isolates_by_user(db_session: AsyncSession) -> None:
    user_a = await make_workspace(db_session)
    user_b = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a1 = await make_wallet(db_session, user_a.id, (currency.id,))
    wallet_a2 = await make_wallet(db_session, user_a.id, (currency.id,))
    wallet_b1 = await make_wallet(db_session, user_b.id, (currency.id,))
    wallet_b2 = await make_wallet(db_session, user_b.id, (currency.id,))
    repo = TransferRepository(db_session)
    await repo.add(make_transfer(user_a.id, wallet_a1.id, wallet_a2.id, currency.id))
    await repo.add(make_transfer(user_b.id, wallet_b1.id, wallet_b2.id, currency.id))
    await db_session.flush()

    items = await repo.list(user_a.id, wallet_id=None, date_from=None, date_to=None, limit=20, offset=0)

    assert len(items) == 1
    assert items[0].workspace_id == user_a.id


async def test_update_replaces_all_fields(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    wallet_c = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, amount=Decimal("10.00"))
    await repo.add(transfer)
    await db_session.flush()

    updated = await repo.update(
        transfer.id,
        user.id,
        from_wallet_id=wallet_b.id,
        to_wallet_id=wallet_c.id,
        currency_id=currency.id,
        amount=Decimal("20.00"),
        occurred_at=datetime(2026, 5, 1, tzinfo=UTC),
        now=datetime(2026, 5, 2, tzinfo=UTC),
    )
    await db_session.flush()

    assert updated is not None
    assert updated.from_wallet_id == wallet_b.id
    assert updated.to_wallet_id == wallet_c.id
    assert updated.amount == Decimal("20.00")
    assert updated.occurred_at == datetime(2026, 5, 1, tzinfo=UTC)
    assert updated.updated_at == datetime(2026, 5, 2, tzinfo=UTC)


async def test_update_unknown_returns_none(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)

    result = await repo.update(
        uuid4(),
        user.id,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("1"),
        occurred_at=DEFAULT_CREATED_AT,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None


async def test_update_with_foreign_workspace_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, owner.id, (currency.id,))
    wallet_b = await make_wallet(db_session, owner.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(owner.id, wallet_a.id, wallet_b.id, currency.id)
    await repo.add(transfer)
    await db_session.flush()

    result = await repo.update(
        transfer.id,
        other.id,
        from_wallet_id=wallet_a.id,
        to_wallet_id=wallet_b.id,
        currency_id=currency.id,
        amount=Decimal("999"),
        occurred_at=DEFAULT_CREATED_AT,
        now=DEFAULT_CREATED_AT,
    )

    assert result is None
    unchanged = await repo.get_by_id(transfer.id, owner.id)
    assert unchanged is not None
    assert unchanged.amount == Decimal("10.00")


async def test_delete_success(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id)
    await repo.add(transfer)
    await db_session.flush()

    deleted = await repo.delete(transfer.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(transfer.id, user.id) is None


async def test_delete_with_foreign_workspace_id_returns_false(db_session: AsyncSession) -> None:
    owner = await make_workspace(db_session)
    other = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, owner.id, (currency.id,))
    wallet_b = await make_wallet(db_session, owner.id, (currency.id,))
    repo = TransferRepository(db_session)
    transfer = make_transfer(owner.id, wallet_a.id, wallet_b.id, currency.id)
    await repo.add(transfer)
    await db_session.flush()

    deleted = await repo.delete(transfer.id, other.id)

    assert deleted is False
    assert await repo.get_by_id(transfer.id, owner.id) is not None


async def test_delete_unknown_returns_false(db_session: AsyncSession) -> None:
    repo = TransferRepository(db_session)

    assert await repo.delete(uuid4(), uuid4()) is False


async def test_deleting_referenced_wallet_is_restricted(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    await repo.add(make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(wallets_table.delete().where(wallets_table.c.id == wallet_a.id))


async def test_deleting_referenced_currency_is_restricted(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    await repo.add(make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(currencies_table.delete().where(currencies_table.c.id == currency.id))


async def test_check_constraint_rejects_nonpositive_amount(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))

    with pytest.raises(IntegrityError):
        await db_session.execute(
            insert(transfers_table).values(
                id=uuid4(),
                workspace_id=user.id,
                from_wallet_id=wallet_a.id,
                to_wallet_id=wallet_b.id,
                currency_id=currency.id,
                amount=Decimal("0"),
                occurred_at=DEFAULT_CREATED_AT,
                created_at=DEFAULT_CREATED_AT,
            )
        )


async def test_check_constraint_rejects_same_wallet(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))

    with pytest.raises(IntegrityError):
        await db_session.execute(
            insert(transfers_table).values(
                id=uuid4(),
                workspace_id=user.id,
                from_wallet_id=wallet.id,
                to_wallet_id=wallet.id,
                currency_id=currency.id,
                amount=Decimal("10"),
                occurred_at=DEFAULT_CREATED_AT,
                created_at=DEFAULT_CREATED_AT,
            )
        )


async def test_balance_delta_aggregates_incoming_and_outgoing_transfers(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet_a = await make_wallet(db_session, user.id, (currency.id,))
    wallet_b = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)
    await repo.add(make_transfer(user.id, wallet_a.id, wallet_b.id, currency.id, amount=Decimal("40.00")))
    await repo.add(make_transfer(user.id, wallet_b.id, wallet_a.id, currency.id, amount=Decimal("15.00")))
    await db_session.flush()

    balance_a = await repo.balance_delta(wallet_a.id, user.id)
    balance_b = await repo.balance_delta(wallet_b.id, user.id)

    assert balance_a == {currency.id: Decimal("-25.00")}
    assert balance_b == {currency.id: Decimal("25.00")}


async def test_balance_delta_empty_for_wallet_without_transfers(db_session: AsyncSession) -> None:
    user = await make_workspace(db_session)
    currency = await make_currency(db_session)
    wallet = await make_wallet(db_session, user.id, (currency.id,))
    repo = TransferRepository(db_session)

    balances = await repo.balance_delta(wallet.id, user.id)

    assert balances == {}
