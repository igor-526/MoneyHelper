import pytest

from core.exceptions import AlreadyExistsError, AuthenticationError, PermissionDeniedError
from core.services.auth import (
    INVALID_CREDENTIALS_MESSAGE,
    REGISTRATION_DISABLED_MESSAGE,
    AuthService,
)
from tests.fakes import FakePasswordHasher, FakeTokenService, FixedClock, InMemoryUserRepository, SequentialIdGenerator

EMAIL = "user@example.com"
PASSWORD = "correct-horse-battery"


def make_service(*, registration_enabled: bool = True) -> tuple[AuthService, InMemoryUserRepository, FixedClock]:
    users = InMemoryUserRepository()
    clock = FixedClock()
    service = AuthService(
        users=users,
        hasher=FakePasswordHasher(),
        issuer=FakeTokenService(),
        verifier=FakeTokenService(),
        clock=clock,
        ids=SequentialIdGenerator(),
        registration_enabled=registration_enabled,
    )
    return service, users, clock


async def test_register_creates_user() -> None:
    service, users, clock = make_service()

    user = await service.register(email=EMAIL, password=PASSWORD)

    assert user.email == EMAIL
    assert user.password_hash == f"hashed:{PASSWORD}"
    assert user.token_version == 0
    assert user.created_at == clock.now()
    assert await users.get_by_id(user.id) == user


async def test_register_rejects_duplicate_email() -> None:
    service, _, _ = make_service()
    await service.register(email=EMAIL, password=PASSWORD)

    with pytest.raises(AlreadyExistsError):
        await service.register(email=EMAIL, password="another-password")


async def test_register_disabled_by_flag() -> None:
    service, users, _ = make_service(registration_enabled=False)

    with pytest.raises(PermissionDeniedError, match=REGISTRATION_DISABLED_MESSAGE):
        await service.register(email=EMAIL, password=PASSWORD)

    assert await users.get_by_email(EMAIL) is None


async def test_login_success_issues_tokens() -> None:
    service, _, _ = make_service()
    registered = await service.register(email=EMAIL, password=PASSWORD)

    user, tokens = await service.login(email=EMAIL, password=PASSWORD)

    assert user == registered
    assert tokens.access_token == f"access:{registered.id}"
    assert tokens.refresh_token == f"refresh:{registered.id}:0"


async def test_login_unknown_email_and_wrong_password_are_identical() -> None:
    service, _, _ = make_service()
    await service.register(email=EMAIL, password=PASSWORD)

    with pytest.raises(AuthenticationError, match=INVALID_CREDENTIALS_MESSAGE) as unknown_exc:
        await service.login(email="nobody@example.com", password=PASSWORD)

    with pytest.raises(AuthenticationError, match=INVALID_CREDENTIALS_MESSAGE) as wrong_exc:
        await service.login(email=EMAIL, password="wrong-password")

    assert str(unknown_exc.value) == str(wrong_exc.value)


async def test_login_unknown_email_still_calls_hasher_verify() -> None:
    """Тайминговая защита: verify() вызывается и для несуществующего email, а не пропускается."""
    hasher = FakePasswordHasher()
    users = InMemoryUserRepository()
    service = AuthService(
        users=users,
        hasher=hasher,
        issuer=FakeTokenService(),
        verifier=FakeTokenService(),
        clock=FixedClock(),
        ids=SequentialIdGenerator(),
        registration_enabled=True,
    )
    calls: list[str] = []
    original_verify = hasher.verify

    async def tracking_verify(password: str, password_hash: str) -> bool:
        calls.append(password_hash)
        return await original_verify(password, password_hash)

    hasher.verify = tracking_verify  # type: ignore[method-assign]

    with pytest.raises(AuthenticationError):
        await service.login(email="nobody@example.com", password=PASSWORD)

    assert len(calls) == 1


async def test_refresh_issues_new_pair() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)
    _, tokens = await service.login(email=EMAIL, password=PASSWORD)

    new_tokens = await service.refresh(tokens.refresh_token)

    assert new_tokens.access_token == f"access:{user.id}"
    assert new_tokens.refresh_token == f"refresh:{user.id}:0"


async def test_refresh_rejects_stale_version() -> None:
    service, users, clock = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)
    _, tokens = await service.login(email=EMAIL, password=PASSWORD)

    await users.bump_token_version(user.id, expected_version=0, now=clock.now())

    with pytest.raises(AuthenticationError):
        await service.refresh(tokens.refresh_token)


async def test_refresh_rejects_garbage_token() -> None:
    service, _, _ = make_service()

    with pytest.raises(AuthenticationError):
        await service.refresh("not-a-token")


async def test_refresh_does_not_invalidate_on_use_parallel_calls_both_succeed() -> None:
    """Refresh скользящий и не инвалидируется обновлением: параллельные вызовы с одним refresh оба успешны."""
    service, _, _ = make_service()
    await service.register(email=EMAIL, password=PASSWORD)
    _, tokens = await service.login(email=EMAIL, password=PASSWORD)

    first = await service.refresh(tokens.refresh_token)
    second = await service.refresh(tokens.refresh_token)

    assert first == second


async def test_logout_bumps_token_version_and_invalidates_refresh() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)
    _, tokens = await service.login(email=EMAIL, password=PASSWORD)

    await service.logout(tokens.refresh_token)

    assert (await service.get_user(user.id)).token_version == 1
    with pytest.raises(AuthenticationError):
        await service.refresh(tokens.refresh_token)


async def test_logout_without_refresh_is_noop() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)

    await service.logout(None)

    assert (await service.get_user(user.id)).token_version == 0


async def test_logout_twice_with_same_refresh_does_not_double_bump() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)
    _, tokens = await service.login(email=EMAIL, password=PASSWORD)

    await service.logout(tokens.refresh_token)
    await service.logout(tokens.refresh_token)

    assert (await service.get_user(user.id)).token_version == 1


async def test_change_password_success_bumps_version_and_issues_tokens() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)

    tokens = await service.change_password(user.id, current_password=PASSWORD, new_password="new-password-1")

    updated = await service.get_user(user.id)
    assert updated.token_version == 1
    assert updated.password_hash == "hashed:new-password-1"
    assert tokens.refresh_token == f"refresh:{user.id}:1"


async def test_change_password_wrong_current_password_is_identical_to_login_error() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)

    with pytest.raises(AuthenticationError, match=INVALID_CREDENTIALS_MESSAGE):
        await service.change_password(user.id, current_password="wrong", new_password="new-password-1")

    assert (await service.get_user(user.id)).token_version == 0


async def test_change_password_old_refresh_stops_working() -> None:
    service, _, _ = make_service()
    user = await service.register(email=EMAIL, password=PASSWORD)
    _, old_tokens = await service.login(email=EMAIL, password=PASSWORD)

    await service.change_password(user.id, current_password=PASSWORD, new_password="new-password-1")

    with pytest.raises(AuthenticationError):
        await service.refresh(old_tokens.refresh_token)


async def test_get_user_unknown_id_raises() -> None:
    service, _, _ = make_service()

    with pytest.raises(AuthenticationError):
        await service.get_user(SequentialIdGenerator(start=999).new())
