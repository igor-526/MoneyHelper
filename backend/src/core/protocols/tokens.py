from typing import Protocol
from uuid import UUID

from core.schemas.auth import AccessClaims, RefreshClaims


class TokenIssuer(Protocol):
    def issue_access(self, user_id: UUID) -> str: ...

    def issue_refresh(self, user_id: UUID, version: int) -> str: ...


class TokenVerifier(Protocol):
    def verify_access(self, token: str) -> AccessClaims:
        """Бросает AuthenticationError, если токен недействителен, чужого типа или просрочен."""
        ...

    def verify_refresh(self, token: str) -> RefreshClaims:
        """Бросает AuthenticationError, если токен недействителен, чужого типа или просрочен."""
        ...
