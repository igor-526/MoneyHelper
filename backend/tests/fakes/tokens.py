from uuid import UUID

from core.exceptions import AuthenticationError
from core.schemas.auth import AccessClaims, RefreshClaims

_INVALID_TOKEN_MESSAGE = "Недействительный или просроченный токен"


class FakeTokenService:
    """Обратимая кодировка вместо JWT — реализует TokenIssuer и TokenVerifier для unit-тестов AuthService."""

    def issue_access(self, user_id: UUID) -> str:
        return f"access:{user_id}"

    def issue_refresh(self, user_id: UUID, version: int) -> str:
        return f"refresh:{user_id}:{version}"

    def verify_access(self, token: str) -> AccessClaims:
        prefix, _, rest = token.partition(":")
        if prefix != "access":
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)
        try:
            return AccessClaims(user_id=UUID(rest))
        except ValueError as exc:
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE) from exc

    def verify_refresh(self, token: str) -> RefreshClaims:
        prefix, _, rest = token.partition(":")
        if prefix != "refresh":
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)
        try:
            user_id_str, version_str = rest.split(":")
            return RefreshClaims(user_id=UUID(user_id_str), version=int(version_str))
        except ValueError as exc:
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE) from exc
