from uuid import UUID

from pydantic import BaseModel

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class AccessClaims(BaseModel):
    user_id: UUID


class RefreshClaims(BaseModel):
    user_id: UUID
    version: int
