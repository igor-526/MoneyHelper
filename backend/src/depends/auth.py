from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends

from api.cookies import ACCESS_COOKIE_NAME
from core.exceptions import AuthenticationError
from core.protocols import Clock, IdGenerator, PasswordHasher, TokenIssuer, TokenVerifier, UserRepository
from core.services.auth import AuthService
from depends.providers import get_clock, get_id_generator
from depends.tokens import get_token_service
from depends.user import get_user_repository
from settings import settings
from utils.password_hasher import Argon2PasswordHasher


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    issuer: Annotated[TokenIssuer, Depends(get_token_service)],
    verifier: Annotated[TokenVerifier, Depends(get_token_service)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> AuthService:
    return AuthService(
        users=users,
        hasher=hasher,
        issuer=issuer,
        verifier=verifier,
        clock=clock,
        ids=ids,
        registration_enabled=settings.registration_enabled,
    )


def get_current_user(
    verifier: Annotated[TokenVerifier, Depends(get_token_service)],
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
) -> UUID:
    """Access проверяется без обращения к БД. Возвращает user_id — сервисы получают его явным аргументом."""
    if access_token is None:
        raise AuthenticationError("Требуется вход")
    return verifier.verify_access(access_token).user_id
