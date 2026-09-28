from decimal import Decimal

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from core.schemas import Money


class Amount(BaseModel):
    value: Money


def test_money_is_serialized_as_string() -> None:
    assert Amount(value=Decimal("12.50")).model_dump_json() == '{"value":"12.50"}'


def test_money_does_not_use_exponent_notation() -> None:
    assert Amount(value=Decimal("1E+3")).model_dump_json() == '{"value":"1000"}'


def test_money_accepts_string_input() -> None:
    assert Amount.model_validate({"value": "0.00000001"}).value == Decimal("0.00000001")


@pytest.mark.parametrize("raw", ["1.123456789", "NaN", "Infinity", "-Infinity", "1" * 25, "abc"])
def test_money_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Money).validate_python(raw)


def test_money_accepts_max_digits() -> None:
    value = Decimal("9" * 16 + "." + "9" * 8)

    assert TypeAdapter(Money).validate_python(value) == value
