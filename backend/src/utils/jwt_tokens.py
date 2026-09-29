from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt

from core.exceptions import AuthenticationError
from core.protocols import Clock
from core.schemas.auth import AccessClaims, RefreshClaims

# Алгоритм подписи зафиксирован (не читается из настроек и не принимается из токена) — это закрывает атаку
# подмены алгоритма (например, на `none`).
ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
_INVALID_TOKEN_MESSAGE = "Недействительный или просроченный токен"


class JwtTokenService:
    """PyJWT, HS256; токены нигде не сохраняются. Срок действия проверяется по `Clock`, а не системным
    временем, поэтому тесты детерминированы."""

    def __init__(self, secret: str, clock: Clock, access_ttl: timedelta, refresh_ttl: timedelta) -> None:
        self._secret = secret
        self._clock = clock
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def issue_access(self, user_id: UUID) -> str:
        return self._encode({"sub": str(user_id), "token_type": ACCESS_TOKEN_TYPE}, self._access_ttl)

    def issue_refresh(self, user_id: UUID, version: int) -> str:
        claims = {"sub": str(user_id), "token_type": REFRESH_TOKEN_TYPE, "ver": version}
        return self._encode(claims, self._refresh_ttl)

    def verify_access(self, token: str) -> AccessClaims:
        payload = self._decode(token, expected_type=ACCESS_TOKEN_TYPE)
        return AccessClaims(user_id=UUID(payload["sub"]))

    def verify_refresh(self, token: str) -> RefreshClaims:
        payload = self._decode(token, expected_type=REFRESH_TOKEN_TYPE)
        version = payload.get("ver")
        if not isinstance(version, int):
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)
        return RefreshClaims(user_id=UUID(payload["sub"]), version=version)

    def _encode(self, claims: dict[str, Any], ttl: timedelta) -> str:
        now = self._clock.now()
        payload = {**claims, "iat": int(now.timestamp()), "exp": int((now + ttl).timestamp())}
        return jwt.encode(payload, self._secret, algorithm=ALGORITHM)

    def _decode(self, token: str, *, expected_type: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                # Срок проверяем сами по Clock ниже — verify_exp отключён, чтобы не зависеть от системных часов.
                options={"verify_exp": False, "require": ["sub", "token_type", "iat", "exp"]},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE) from exc

        if payload.get("token_type") != expected_type:
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)
        try:
            UUID(sub)
        except ValueError as exc:
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE) from exc

        exp = payload.get("exp")
        if not isinstance(exp, int) or exp <= int(self._clock.now().timestamp()):
            raise AuthenticationError(_INVALID_TOKEN_MESSAGE)

        return payload
