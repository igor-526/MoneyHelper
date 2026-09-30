from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from core.entities import CategoryType
from core.exceptions import ClientError
from core.protocols import CurrencyRepository, TransactionRepository
from core.services.analytics_dimensions import DIMENSIONS
from core.services.rate_averaging import average_rates

INVALID_DATE_RANGE_MESSAGE = "date_from не может быть позже date_to"
UNKNOWN_DISPLAY_CURRENCY_MESSAGE = "Неизвестная валюта отображения"


def _round(amount: Decimal, decimal_places: int) -> Decimal:
    return amount.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)


class AnalyticsService:
    def __init__(self, transactions: TransactionRepository, currencies: CurrencyRepository) -> None:
        self._transactions = transactions
        self._currencies = currencies

    async def get_analytics(
        self,
        workspace_id: UUID,
        *,
        display_currency_id: UUID,
        date_from: datetime,
        date_to: datetime,
        group_by: str,
        wallet_id: UUID | None,
        category_id: UUID | None,
        currency_id: UUID | None,
        type: CategoryType | None,
    ) -> tuple[list[tuple[UUID, Decimal, Decimal]], list[UUID]]:
        if date_from > date_to:
            raise ClientError(INVALID_DATE_RANGE_MESSAGE)
        display_currency = await self._currencies.get_by_id(display_currency_id)
        if display_currency is None:
            raise ClientError(UNKNOWN_DISPLAY_CURRENCY_MESSAGE)

        legs = await self._transactions.list_legs_for_analytics(
            workspace_id,
            date_from=date_from,
            date_to=date_to,
            wallet_id=wallet_id,
            category_id=category_id,
            currency_id=currency_id,
            type=type,
        )
        needed = {leg.currency_id for leg in legs} - {display_currency_id}
        rates = (
            await self._average_rates(workspace_id, display_currency_id, needed, date_from, date_to) if needed else {}
        )

        dimension = DIMENSIONS[group_by]
        totals: dict[UUID, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
        unconverted: set[UUID] = set()
        for leg in legs:
            if leg.currency_id == display_currency_id:
                converted = leg.amount
            elif leg.currency_id in rates:
                converted = leg.amount * rates[leg.currency_id]
            else:
                unconverted.add(leg.currency_id)
                continue
            bucket = totals[dimension.key(leg)]
            bucket[0 if leg.category_type is CategoryType.INCOME else 1] += converted

        buckets = [
            (key, _round(income, display_currency.decimal_places), _round(expense, display_currency.decimal_places))
            for key, (income, expense) in totals.items()
        ]
        return buckets, sorted(unconverted, key=str)

    async def _average_rates(
        self, workspace_id: UUID, target_id: UUID, source_ids: set[UUID], date_from: datetime, date_to: datetime
    ) -> dict[UUID, Decimal]:
        topup_legs = await self._transactions.list_topup_legs_for_rates(
            workspace_id, date_from=date_from, date_to=date_to
        )
        return average_rates(topup_legs, target_id, source_ids)
