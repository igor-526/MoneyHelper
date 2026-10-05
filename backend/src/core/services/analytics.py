from collections import defaultdict
from datetime import date, datetime, tzinfo
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from core.entities import CategoryType
from core.exceptions import ClientError, NotFoundError
from core.protocols import CurrencyRepository, TransactionRepository, WalletCurrencyReader, WorkspaceCurrencyReader
from core.services.analytics_dimensions import DIMENSIONS
from core.services.rate_averaging import average_rates

INVALID_DATE_RANGE_MESSAGE = "date_from не может быть позже date_to"
INVALID_DISPLAY_CURRENCY_MESSAGE = "Недопустимая валюта отображения"
WORKSPACE_NOT_FOUND_MESSAGE = "Воркспейс не найден"


def _round(amount: Decimal, decimal_places: int) -> Decimal:
    return amount.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)


class AnalyticsService:
    def __init__(
        self,
        transactions: TransactionRepository,
        currencies: CurrencyRepository,
        wallets: WalletCurrencyReader,
        workspaces: WorkspaceCurrencyReader,
    ) -> None:
        self._transactions = transactions
        self._currencies = currencies
        self._wallets = wallets
        self._workspaces = workspaces

    async def get_analytics(
        self,
        workspace_id: UUID,
        *,
        display_currency_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        group_by: str,
        wallet_id: UUID | None,
        category_id: UUID | None,
        currency_id: UUID | None,
        type: CategoryType | None,
        tz: tzinfo,
    ) -> tuple[UUID, list[tuple[UUID | date, Decimal, Decimal]], list[UUID]]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClientError(INVALID_DATE_RANGE_MESSAGE)
        workspace_currency_id = await self._workspaces.get_currency_id(workspace_id)
        if workspace_currency_id is None:
            raise NotFoundError(WORKSPACE_NOT_FOUND_MESSAGE)
        currency_id_by_wallet = await self._wallets.get_currency_id_by_wallet(workspace_id)
        display_currency_id = display_currency_id if display_currency_id is not None else workspace_currency_id
        if display_currency_id != workspace_currency_id and display_currency_id not in currency_id_by_wallet.values():
            raise ClientError(INVALID_DISPLAY_CURRENCY_MESSAGE)
        display_currency = await self._currencies.get_by_id(display_currency_id)
        if display_currency is None:
            raise ClientError(INVALID_DISPLAY_CURRENCY_MESSAGE)

        legs = await self._transactions.list_legs_for_analytics(
            workspace_id,
            date_from=date_from,
            date_to=date_to,
            wallet_id=wallet_id,
            category_id=category_id,
            currency_id=currency_id,
            type=type,
        )
        legs = [leg for leg in legs if currency_id_by_wallet.get(leg.wallet_id) == leg.currency_id]
        needed = {leg.currency_id for leg in legs} - {display_currency_id}
        rates = (
            await self._average_rates(workspace_id, display_currency_id, needed, date_from, date_to) if needed else {}
        )

        dimension = DIMENSIONS[group_by]
        totals: dict[UUID | date, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
        unconverted: set[UUID] = set()
        for leg in legs:
            if leg.currency_id == display_currency_id:
                converted = leg.amount
            elif leg.currency_id in rates:
                converted = leg.amount * rates[leg.currency_id]
            else:
                unconverted.add(leg.currency_id)
                continue
            bucket = totals[dimension.key(leg, tz)]
            bucket[0 if leg.category_type is CategoryType.INCOME else 1] += converted

        buckets = [
            (key, _round(income, display_currency.decimal_places), _round(expense, display_currency.decimal_places))
            for key, (income, expense) in totals.items()
        ]
        return display_currency_id, buckets, sorted(unconverted, key=str)

    async def _average_rates(
        self,
        workspace_id: UUID,
        target_id: UUID,
        source_ids: set[UUID],
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> dict[UUID, Decimal]:
        topup_legs = await self._transactions.list_topup_legs_for_rates(
            workspace_id, wallet_id=None, date_from=date_from, date_to=date_to
        )
        return average_rates(topup_legs, target_id, source_ids)
