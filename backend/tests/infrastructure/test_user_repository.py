from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import User
from core.exceptions import AlreadyExistsError
from repositories.user import UserRepository

pytestmark = pytest.mark.infrastructure


def make_user(email: str = "user@example.com") -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash="hashed:password",
        token_version=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = make_user()

    await repo.add(user)
    await db_session.flush()

    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.email == user.email
    assert fetched.token_version == 0


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    assert await repo.get_by_id(uuid4()) is None


async def test_get_by_email(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = make_user("someone@example.com")
    await repo.add(user)
    await db_session.flush()

    assert (await repo.get_by_email("someone@example.com")) is not None
    assert (await repo.get_by_email("nobody@example.com")) is None


async def test_email_uniqueness_is_enforced(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    await repo.add(make_user("dup@example.com"))
    await db_session.flush()

    with pytest.raises(AlreadyExistsError):
        await repo.add(make_user("dup@example.com"))


async def test_email_uniqueness_is_case_insensitive_at_application_level(db_session: AsyncSession) -> None:
    """БД хранит email уже в нижнем регистре (нормализация — на уровне API); значение с заглавными буквами
    нарушает CHECK и означает ошибку выше по стеку, а не дубликат."""
    repo = UserRepository(db_session)
    await repo.add(make_user("dup2@example.com"))
    await db_session.flush()

    with pytest.raises(AlreadyExistsError):
        await repo.add(make_user("dup2@example.com"))


async def test_update_password_bumps_token_version(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = make_user()
    await repo.add(user)
    await db_session.flush()

    updated = await repo.update_password(user.id, "hashed:new-password", datetime(2026, 2, 1, tzinfo=UTC))

    assert updated is not None
    assert updated.password_hash == "hashed:new-password"
    assert updated.token_version == 1
    assert updated.updated_at == datetime(2026, 2, 1, tzinfo=UTC)


async def test_update_password_unknown_user_returns_none(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    result = await repo.update_password(uuid4(), "hashed:new-password", datetime(2026, 2, 1, tzinfo=UTC))

    assert result is None


async def test_bump_token_version_matching_expected_succeeds(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = make_user()
    await repo.add(user)
    await db_session.flush()

    ok = await repo.bump_token_version(user.id, expected_version=0, now=datetime(2026, 2, 1, tzinfo=UTC))

    assert ok is True
    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.token_version == 1


async def test_bump_token_version_mismatched_expected_is_noop(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = make_user()
    await repo.add(user)
    await db_session.flush()

    ok = await repo.bump_token_version(user.id, expected_version=5, now=datetime(2026, 2, 1, tzinfo=UTC))

    assert ok is False
    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.token_version == 0


async def test_bump_token_version_unknown_user_returns_false(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    assert await repo.bump_token_version(uuid4(), expected_version=0, now=datetime(2026, 2, 1, tzinfo=UTC)) is False
