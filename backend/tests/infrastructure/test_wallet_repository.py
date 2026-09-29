from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import Category, CategoryType, Currency, Transaction, TransactionLeg, Transfer, User, Wallet
from core.exceptions import ConflictError
from models import currencies as currencies_table
from models import wallet_currencies as wallet_currencies_table
from repositories.category import CategoryRepository
from repositories.currency import CurrencyRepository
from repositories.transaction import TransactionRepository
from repositories.transfer import TransferRepository
from repositories.user import UserRepository
from repositories.wallet import WalletRepository

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


async def make_currency(db_session: AsyncSession, code: str) -> Currency:
    currency = Currency(id=uuid4(), code=code, name=code, decimal_places=2)
    await CurrencyRepository(db_session).upsert_many([currency])
    await db_session.flush()
    return currency


def make_wallet(
    user_id: UUID,
    currency_ids: tuple[UUID, ...],
    *,
    name: str = "Кошелёк",
    icon: str = "wallet",
    created_at: datetime = DEFAULT_CREATED_AT,
) -> Wallet:
    return Wallet(id=uuid4(), user_id=user_id, name=name, icon=icon, currency_ids=currency_ids, created_at=created_at)


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,), name="Наличные")

    added = await repo.add(wallet)
    await db_session.flush()

    assert added.currency_ids == (rub.id,)
    fetched = await repo.get_by_id(wallet.id, user.id)
    assert fetched is not None
    assert fetched.name == "Наличные"
    assert fetched.currency_ids == (rub.id,)


async def test_get_by_id_unknown_wallet_returns_none(db_session: AsyncSession) -> None:
    repo = WalletRepository(db_session)

    assert await repo.get_by_id(uuid4(), uuid4()) is None


async def test_currency_ids_are_ordered_by_currency_code(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    usdt = await make_currency(db_session, "USDT")
    repo = WalletRepository(db_session)
    # Намеренно вставлены не в алфавитном порядке кода.
    wallet = make_wallet(user.id, (rub.id, usdt.id, cny.id), name="Мультивалютный")
    await repo.add(wallet)
    await db_session.flush()

    fetched = await repo.get_by_id(wallet.id, user.id)

    assert fetched is not None
    assert fetched.currency_ids == (cny.id, rub.id, usdt.id)


async def test_list_is_sorted_by_created_at_then_id(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    first = make_wallet(user.id, (rub.id,), name="A", created_at=later)
    second = make_wallet(user.id, (rub.id,), name="B", created_at=same_moment)
    third = make_wallet(user.id, (rub.id,), name="C", created_at=same_moment)
    for wallet in (first, second, third):
        await repo.add(wallet)
    await db_session.flush()

    items = await repo.list(user.id, limit=20, offset=0)

    same_moment_ids_sorted = sorted([second.id, third.id])
    assert [item.id for item in items] == [*same_moment_ids_sorted, first.id]


async def test_count_matches_user_wallets(db_session: AsyncSession) -> None:
    user_a = await make_user(db_session)
    user_b = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    await repo.add(make_wallet(user_a.id, (rub.id,), name="A1"))
    await repo.add(make_wallet(user_a.id, (rub.id,), name="A2"))
    await repo.add(make_wallet(user_b.id, (rub.id,), name="B1"))
    await db_session.flush()

    assert await repo.count(user_a.id) == 2
    assert await repo.count(user_b.id) == 1


async def test_update_replaces_name_icon_and_currency_set(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    cny = await make_currency(db_session, "CNY")
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,), name="Старое")
    await repo.add(wallet)
    await db_session.flush()

    updated = await repo.update(
        wallet.id, user.id, name="Новое", icon="banknote", currency_ids=[cny.id], now=datetime(2026, 2, 1, tzinfo=UTC)
    )
    await db_session.flush()

    assert updated is not None
    assert updated.name == "Новое"
    assert updated.icon == "banknote"
    assert updated.currency_ids == (cny.id,)
    assert updated.updated_at == datetime(2026, 2, 1, tzinfo=UTC)


async def test_update_unknown_wallet_returns_none(db_session: AsyncSession) -> None:
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)

    result = await repo.update(
        uuid4(), uuid4(), name="X", icon="wallet", currency_ids=[rub.id], now=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert result is None


async def test_update_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(owner.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    result = await repo.update(
        wallet.id, other.id, name="Чужое", icon="banknote", currency_ids=[rub.id], now=datetime(2026, 2, 1, tzinfo=UTC)
    )

    assert result is None
    unchanged = await repo.get_by_id(wallet.id, owner.id)
    assert unchanged is not None
    assert unchanged.name == "Кошелёк"


async def test_get_by_id_with_foreign_user_id_returns_none(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(owner.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    assert await repo.get_by_id(wallet.id, other.id) is None


async def test_delete_success(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    deleted = await repo.delete(wallet.id, user.id)
    await db_session.flush()

    assert deleted is True
    assert await repo.get_by_id(wallet.id, user.id) is None


async def test_delete_with_foreign_user_id_returns_false(db_session: AsyncSession) -> None:
    owner = await make_user(db_session)
    other = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(owner.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    deleted = await repo.delete(wallet.id, other.id)

    assert deleted is False
    assert await repo.get_by_id(wallet.id, owner.id) is not None


async def test_delete_unknown_wallet_returns_false(db_session: AsyncSession) -> None:
    repo = WalletRepository(db_session)

    assert await repo.delete(uuid4(), uuid4()) is False


async def test_deleting_wallet_cascades_to_wallet_currencies(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    await repo.delete(wallet.id, user.id)
    await db_session.flush()

    query = select(wallet_currencies_table).where(wallet_currencies_table.c.wallet_id == wallet.id)
    rows = (await db_session.execute(query)).all()
    assert rows == []


async def test_inserting_wallet_currency_with_unknown_currency_id_is_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (uuid4(),))

    with pytest.raises(IntegrityError):
        await repo.add(wallet)


async def test_deleting_referenced_currency_is_restricted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,))
    await repo.add(wallet)
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(delete(currencies_table).where(currencies_table.c.id == rub.id))


async def test_delete_wallet_with_transactions_raises_conflict_error(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    wallet_repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, (rub.id,))
    await wallet_repo.add(wallet)
    category = await CategoryRepository(db_session).add(
        Category(
            id=uuid4(),
            user_id=user.id,
            type=CategoryType.INCOME,
            name="Зарплата",
            icon="wallet",
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await TransactionRepository(db_session).add(
        Transaction(
            id=uuid4(),
            user_id=user.id,
            wallet_id=wallet.id,
            category_id=category.id,
            legs=(TransactionLeg(currency_id=rub.id, amount=Decimal("10.00")),),
            occurred_at=DEFAULT_CREATED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await db_session.flush()

    with pytest.raises(ConflictError):
        await wallet_repo.delete(wallet.id, user.id)


async def test_delete_from_wallet_with_transfer_raises_conflict_error(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    wallet_repo = WalletRepository(db_session)
    wallet_a = make_wallet(user.id, (rub.id,), name="A")
    wallet_b = make_wallet(user.id, (rub.id,), name="B")
    await wallet_repo.add(wallet_a)
    await wallet_repo.add(wallet_b)
    await TransferRepository(db_session).add(
        Transfer(
            id=uuid4(),
            user_id=user.id,
            from_wallet_id=wallet_a.id,
            to_wallet_id=wallet_b.id,
            currency_id=rub.id,
            amount=Decimal("10.00"),
            occurred_at=DEFAULT_CREATED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await db_session.flush()

    with pytest.raises(ConflictError):
        await wallet_repo.delete(wallet_a.id, user.id)


async def test_delete_to_wallet_with_transfer_raises_conflict_error(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    rub = await make_currency(db_session, "RUB")
    wallet_repo = WalletRepository(db_session)
    wallet_a = make_wallet(user.id, (rub.id,), name="A")
    wallet_b = make_wallet(user.id, (rub.id,), name="B")
    await wallet_repo.add(wallet_a)
    await wallet_repo.add(wallet_b)
    await TransferRepository(db_session).add(
        Transfer(
            id=uuid4(),
            user_id=user.id,
            from_wallet_id=wallet_a.id,
            to_wallet_id=wallet_b.id,
            currency_id=rub.id,
            amount=Decimal("10.00"),
            occurred_at=DEFAULT_CREATED_AT,
            created_at=DEFAULT_CREATED_AT,
        )
    )
    await db_session.flush()

    with pytest.raises(ConflictError):
        await wallet_repo.delete(wallet_b.id, user.id)
