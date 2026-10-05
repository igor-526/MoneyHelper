from datetime import date, tzinfo
from uuid import UUID

from core.entities import LegRecord
from core.protocols import AnalyticsDimension


class WalletDimension:
    def key(self, record: LegRecord, tz: tzinfo) -> UUID:
        return record.wallet_id


class CategoryDimension:
    def key(self, record: LegRecord, tz: tzinfo) -> UUID:
        return record.category_id


class CurrencyDimension:
    def key(self, record: LegRecord, tz: tzinfo) -> UUID:
        return record.currency_id


class DayDimension:
    def key(self, record: LegRecord, tz: tzinfo) -> date:
        return record.occurred_at.astimezone(tz).date()


DIMENSIONS: dict[str, AnalyticsDimension] = {
    "wallet": WalletDimension(),
    "category": CategoryDimension(),
    "currency": CurrencyDimension(),
    "day": DayDimension(),
}
