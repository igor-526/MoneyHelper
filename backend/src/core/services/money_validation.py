from decimal import Decimal
from uuid import UUID

from core.entities import Currency
from core.exceptions import ClientError
from core.protocols import CurrencyRepository


def ensure_amount_precision(amount: Decimal, currency: Currency) -> None:
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0 and -exponent > currency.decimal_places:
        raise ClientError(
            f"Сумма содержит больше {currency.decimal_places} знаков после запятой, "
            f"допустимых для валюты {currency.code}"
        )


async def validate_leg_amount(currencies: CurrencyRepository, currency_id: UUID, amount: Decimal) -> Currency:
    if amount <= 0:
        raise ClientError("Сумма должна быть положительной")
    currency = await currencies.get_by_id(currency_id)
    if currency is None:
        raise ClientError("Неизвестная валюта операции")
    ensure_amount_precision(amount, currency)
    return currency
