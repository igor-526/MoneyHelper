from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from core.schemas.auth import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

MAX_EMAIL_LENGTH = 254


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return _normalize_email(value)

    @field_validator("email")
    @classmethod
    def validate_email_length(cls, value: str) -> str:
        if len(value) > MAX_EMAIL_LENGTH:
            raise ValueError(f"email длиннее {MAX_EMAIL_LENGTH} символов")
        return value


class LoginRequest(BaseModel):
    # Формат намеренно не проверяется как email: некорректный формат должен давать тот же ответ
    # «Неверный email или пароль», что и неизвестный адрес, а не отдельную ошибку валидации.
    email: str = Field(min_length=1, max_length=MAX_EMAIL_LENGTH)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return _normalize_email(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime
