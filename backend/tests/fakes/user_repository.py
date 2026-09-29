from datetime import datetime
from uuid import UUID

from core.entities import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def add(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)

    async def update_password(self, user_id: UUID, password_hash: str, now: datetime) -> User | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        updated = user.model_copy(
            update={"password_hash": password_hash, "token_version": user.token_version + 1, "updated_at": now}
        )
        self._users[user_id] = updated
        return updated

    async def bump_token_version(self, user_id: UUID, expected_version: int, now: datetime) -> bool:
        user = self._users.get(user_id)
        if user is None or user.token_version != expected_version:
            return False
        self._users[user_id] = user.model_copy(update={"token_version": user.token_version + 1, "updated_at": now})
        return True
