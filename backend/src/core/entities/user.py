from core.entities.base import Entity, TimestampMixin


class User(Entity, TimestampMixin):
    email: str
    password_hash: str
    token_version: int = 0
