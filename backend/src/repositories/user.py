from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import User
from core.exceptions import AlreadyExistsError
from models import users


def _map_row(row: Row[Any]) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        token_version=row.token_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        try:
            await self._session.execute(
                insert(users).values(
                    id=user.id,
                    email=user.email,
                    password_hash=user.password_hash,
                    token_version=user.token_version,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
            )
        except IntegrityError as exc:
            raise AlreadyExistsError("Пользователь с таким email уже зарегистрирован") from exc
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = (await self._session.execute(select(users).where(users.c.id == user_id))).first()
        return _map_row(row) if row is not None else None

    async def get_by_email(self, email: str) -> User | None:
        row = (await self._session.execute(select(users).where(users.c.email == email))).first()
        return _map_row(row) if row is not None else None

    async def update_password(self, user_id: UUID, password_hash: str, now: datetime) -> User | None:
        result = await self._session.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(password_hash=password_hash, token_version=users.c.token_version + 1, updated_at=now)
            .returning(users)
        )
        row = result.first()
        return _map_row(row) if row is not None else None

    async def bump_token_version(self, user_id: UUID, expected_version: int, now: datetime) -> bool:
        result = await self._session.execute(
            update(users)
            .where(users.c.id == user_id, users.c.token_version == expected_version)
            .values(token_version=users.c.token_version + 1, updated_at=now)
            .returning(users.c.id)
        )
        return result.first() is not None
