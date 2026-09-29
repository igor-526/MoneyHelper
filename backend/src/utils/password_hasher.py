import asyncio

from argon2 import PasswordHasher as Argon2PasswordHasher_
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    """argon2id; хеширование и проверка выполняются вне event loop (`asyncio.to_thread`)."""

    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher_()

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password: str, password_hash: str) -> bool:
        def _verify() -> bool:
            try:
                return self._hasher.verify(password_hash, password)
            except VerifyMismatchError, VerificationError, InvalidHashError:
                return False

        return await asyncio.to_thread(_verify)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)
