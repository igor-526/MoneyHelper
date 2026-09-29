from uuid import UUID

from core.entities import LegRecord
from core.protocols import AnalyticsDimension


class WalletDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.wallet_id


class CategoryDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.category_id


class CurrencyDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.currency_id


DIMENSIONS: dict[str, AnalyticsDimension] = {
    "wallet": WalletDimension(),
    "category": CategoryDimension(),
    "currency": CurrencyDimension(),
}
