from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

RATE_MAX_DIGITS = 28
RATE_DECIMAL_PLACES = 10

Rate = Annotated[
    Decimal,
    Field(max_digits=RATE_MAX_DIGITS, decimal_places=RATE_DECIMAL_PLACES, allow_inf_nan=False),
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
]
