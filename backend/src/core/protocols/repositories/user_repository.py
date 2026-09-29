from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.entities import User


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def update_password(self, user_id: UUID, password_hash: str, now: datetime) -> User | None:
        """Сохраняет новый хеш пароля и увеличивает token_version на 1. None, если пользователь не найден."""
        ...

    async def bump_token_version(self, user_id: UUID, expected_version: int, now: datetime) -> bool:
        """Увеличивает token_version на 1, только если текущее значение равно expected_version (без двойного
        увеличения при повторном вызове с тем же refresh). True, если версия была увеличена."""
        ...
