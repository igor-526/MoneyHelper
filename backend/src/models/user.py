from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID

from utils.basemodel import metadata

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("token_version", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    CheckConstraint("token_version >= 0", name="ck_users_token_version_non_negative"),
)
