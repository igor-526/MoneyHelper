import re
from functools import cached_property
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ORIGIN_PATTERN = re.compile(r"^https?://[^/\s?#]+$")

# Годится только для локальной разработки: вне development использование этого значения запрещено.
DEV_DEFAULT_JWT_SECRET = "insecure-development-secret-key-change-me-please"
JWT_SECRET_MIN_LENGTH = 32


class Settings(BaseSettings):
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    app_title: str = Field(default="FastAPI Template", alias="APP_TITLE")

    sentry_enabled: bool = Field(default=False, alias="SENTRY_ENABLED")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE", ge=0.0, le=1.0)
    sentry_release: str | None = Field(default=None, alias="SENTRY_RELEASE")

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="CORS_ORIGINS")

    postgres_user: str = Field(default="app", alias="POSTGRES_USER")
    postgres_password: str = Field(default="app", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="app", alias="POSTGRES_DB")

    jwt_secret: str = Field(default=DEV_DEFAULT_JWT_SECRET, alias="JWT_SECRET")
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES", gt=0)
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS", gt=0)
    cookie_secure: bool | None = Field(default=None, alias="COOKIE_SECURE")
    cookie_domain: str | None = Field(default=None, alias="COOKIE_DOMAIN")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax", alias="COOKIE_SAMESITE")
    registration_enabled: bool = Field(default=False, alias="REGISTRATION_ENABLED")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def normalize_cookie_samesite(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        for origin in value:
            if not ORIGIN_PATTERN.fullmatch(origin):
                raise ValueError(f"CORS_ORIGINS: некорректный origin {origin!r}, ожидается scheme://host[:port]")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        if self.sentry_enabled and not self.sentry_dsn:
            raise ValueError("SENTRY_DSN is required when SENTRY_ENABLED=true")
        return self

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> Settings:
        if self.environment != "development":
            if self.jwt_secret == DEV_DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be set outside development")
            if len(self.jwt_secret) < JWT_SECRET_MIN_LENGTH:
                raise ValueError(f"JWT_SECRET must be at least {JWT_SECRET_MIN_LENGTH} characters outside development")
        return self

    @model_validator(mode="after")
    def validate_cookie_samesite(self) -> Settings:
        if self.cookie_samesite == "none" and not self.cookie_secure_resolved:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        return self

    @cached_property
    def cookie_secure_resolved(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else self.environment != "development"

    @cached_property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
