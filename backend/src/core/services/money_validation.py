from decimal import Decimal

from core.entities import Currency
from core.exceptions import ClientError


def ensure_amount_precision(amount: Decimal, currency: Currency) -> None:
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0 and -exponent > currency.decimal_places:
        raise ClientError(
            f"Сумма содержит больше {currency.decimal_places} знаков после запятой, "
            f"допустимых для валюты {currency.code}"
        )
