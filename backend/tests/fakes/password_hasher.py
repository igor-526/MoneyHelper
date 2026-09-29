class FakePasswordHasher:
    """Без настоящей криптографии — для unit-тестов, где важна только сама логика сервиса."""

    def __init__(self) -> None:
        self.rehash_needed: set[str] = set()

    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"

    def needs_rehash(self, password_hash: str) -> bool:
        return password_hash in self.rehash_needed
