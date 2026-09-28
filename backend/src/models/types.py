from sqlalchemy import Numeric

from core.schemas.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS

MONEY = Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES)
