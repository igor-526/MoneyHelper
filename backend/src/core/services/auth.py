from uuid import UUID

from core.entities import User
from core.exceptions import AlreadyExistsError, AuthenticationError, PermissionDeniedError
from core.protocols import Clock, IdGenerator, PasswordHasher, TokenIssuer, TokenVerifier, UserRepository
from core.schemas.auth import TokenPair

# Один и тот же текст для неверного email/пароля при входе и для неверного текущего пароля при смене:
# не даём понять по тексту ответа, что именно не совпало.
INVALID_CREDENTIALS_MESSAGE = "Неверный email или пароль"
REGISTRATION_DISABLED_MESSAGE = "Регистрация недоступна"
INVALID_OR_EXPIRED_TOKEN_MESSAGE = "Недействительный или просроченный токен"

# argon2id-хеш заведомо неверного пароля. Используется, когда email не найден, чтобы verify() занял
# столько же времени, сколько и для существующего пользователя (тайминг не выдаёт наличие email).
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$LfVaXnQSmpYuRmwniZNy3Q$Bem2POpEhlVUT2zr4rFQmJAPtA5S1onhzJnvv7tjQM4"
)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        issuer: TokenIssuer,
        verifier: TokenVerifier,
        clock: Clock,
        ids: IdGenerator,
        registration_enabled: bool,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._issuer = issuer
        self._verifier = verifier
        self._clock = clock
        self._ids = ids
        self._registration_enabled = registration_enabled

    async def register(self, email: str, password: str) -> User:
        if not self._registration_enabled:
            raise PermissionDeniedError(REGISTRATION_DISABLED_MESSAGE)

        if await self._users.get_by_email(email) is not None:
            raise AlreadyExistsError("Пользователь с таким email уже зарегистрирован")

        now = self._clock.now()
        user = User(
            id=self._ids.new(),
            email=email,
            password_hash=await self._hasher.hash(password),
            token_version=0,
            created_at=now,
        )
        return await self._users.add(user)

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self._users.get_by_email(email)
        # Неизвестный email проверяется против фиктивного хеша — та же по времени работа, что и для
        # существующего пользователя.
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_valid = await self._hasher.verify(password, password_hash)

        if user is None or not password_valid:
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)

        return user, self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = self._verifier.verify_refresh(refresh_token)
        user = await self._users.get_by_id(claims.user_id)

        if user is None or user.token_version != claims.version:
            raise AuthenticationError(INVALID_OR_EXPIRED_TOKEN_MESSAGE)

        return self._issue_tokens(user)

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            claims = self._verifier.verify_refresh(refresh_token)
        except AuthenticationError:
            return
        # Условный UPDATE: повторный logout с тем же refresh не увеличивает версию ещё раз.
        await self._users.bump_token_version(claims.user_id, claims.version, self._clock.now())

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> TokenPair:
        user = await self._users.get_by_id(user_id)
        if user is None or not await self._hasher.verify(current_password, user.password_hash):
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)

        updated = await self._users.update_password(user.id, await self._hasher.hash(new_password), self._clock.now())
        if updated is None:
            raise AuthenticationError(INVALID_OR_EXPIRED_TOKEN_MESSAGE)

        return self._issue_tokens(updated)

    async def get_user(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError(INVALID_OR_EXPIRED_TOKEN_MESSAGE)
        return user

    def _issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=self._issuer.issue_access(user.id),
            refresh_token=self._issuer.issue_refresh(user.id, user.token_version),
        )
