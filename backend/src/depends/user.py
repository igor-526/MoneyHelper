from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.protocols import UserRepository
from repositories.user import UserRepository as SqlUserRepository
from utils.database import get_session


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return SqlUserRepository(session)
