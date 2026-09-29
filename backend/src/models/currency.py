from sqlalchemy import CheckConstraint, Column, SmallInteger, String, Table
from sqlalchemy.dialects.postgresql import UUID

from utils.basemodel import metadata

currencies = Table(
    "currencies",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String(10), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("decimal_places", SmallInteger, nullable=False),
    CheckConstraint("code = upper(code)", name="ck_currencies_code_uppercase"),
    CheckConstraint("decimal_places BETWEEN 0 AND 8", name="ck_currencies_decimal_places_range"),
)
