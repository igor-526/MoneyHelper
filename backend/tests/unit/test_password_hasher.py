from utils.password_hasher import Argon2PasswordHasher


async def test_hash_can_be_verified() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = await hasher.hash("correct-horse-battery")

    assert await hasher.verify("correct-horse-battery", password_hash) is True


async def test_verify_rejects_wrong_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = await hasher.hash("correct-horse-battery")

    assert await hasher.verify("wrong-password", password_hash) is False


async def test_verify_rejects_garbage_hash() -> None:
    hasher = Argon2PasswordHasher()

    assert await hasher.verify("anything", "not-a-real-hash") is False


async def test_hash_uses_argon2id() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = await hasher.hash("correct-horse-battery")

    assert password_hash.startswith("$argon2id$")


async def test_needs_rehash_false_for_fresh_hash() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = await hasher.hash("correct-horse-battery")

    assert hasher.needs_rehash(password_hash) is False
