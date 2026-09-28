from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

MONEY_MAX_DIGITS = 24
MONEY_DECIMAL_PLACES = 8

Money = Annotated[
    Decimal,
    Field(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, allow_inf_nan=False),
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
]
