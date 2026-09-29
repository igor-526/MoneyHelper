from typing import Protocol


class PasswordHasher(Protocol):
    async def hash(self, password: str) -> str:
        """Хеширует пароль. Выполняется вне event loop."""
        ...

    async def verify(self, password: str, password_hash: str) -> bool:
        """Сверяет пароль с хешем. Выполняется вне event loop."""
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """True, если хеш использует устаревшие параметры и его стоит пересчитать."""
        ...
