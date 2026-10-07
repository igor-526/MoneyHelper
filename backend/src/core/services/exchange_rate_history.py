from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from core.exceptions import ClientError, NotFoundError
from core.protocols import CurrencyLookup, ExchangeRateHistoryReader, WalletCurrencyReader, WorkspaceCurrencyReader
from core.schemas.rate import RATE_DECIMAL_PLACES

INVALID_BASE_CURRENCY_MESSAGE = "Недопустимая валюта курса"
INVALID_DATE_RANGE_MESSAGE = "date_from не может быть позже date_to"
RUB_NOT_FOUND_MESSAGE = "Валюта RUB не найдена"
WORKSPACE_NOT_FOUND_MESSAGE = "Воркспейс не найден"
RATE_QUANTUM = Decimal(1).scaleb(-RATE_DECIMAL_PLACES)


@dataclass(frozen=True)
class ExchangeRatePoint:
    date: date
    rate: Decimal


@dataclass(frozen=True)
class ExchangeRateHistory:
    base_currency_id: UUID
    quote_currency_id: UUID
    points: tuple[ExchangeRatePoint, ...]


class ExchangeRateHistoryService:
    def __init__(
        self,
        history: ExchangeRateHistoryReader,
        currencies: CurrencyLookup,
        wallets: WalletCurrencyReader,
        workspaces: WorkspaceCurrencyReader,
    ) -> None:
        self._history = history
        self._currencies = currencies
        self._wallets = wallets
        self._workspaces = workspaces

    async def get_history(
        self,
        workspace_id: UUID,
        *,
        base_currency_id: UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> ExchangeRateHistory:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ClientError(INVALID_DATE_RANGE_MESSAGE)
        workspace_currency_id = await self._workspaces.get_currency_id(workspace_id)
        if workspace_currency_id is None:
            raise NotFoundError(WORKSPACE_NOT_FOUND_MESSAGE)
        rub = await self._currencies.get_by_code("RUB")
        if rub is None:
            raise NotFoundError(RUB_NOT_FOUND_MESSAGE)
        base = await self._currencies.get_by_id(base_currency_id)
        wallet_currency_ids = set((await self._wallets.get_currency_id_by_wallet(workspace_id)).values())
        allowed_currency_ids = wallet_currency_ids | {workspace_currency_id}
        if base is None or base.id == rub.id or base.id not in allowed_currency_ids:
            raise ClientError(INVALID_BASE_CURRENCY_MESSAGE)

        legs = await self._history.list_dated_topup_legs(workspace_id, date_from=date_from, date_to=date_to)
        legs_by_transaction: dict[UUID, dict[UUID, Decimal]] = defaultdict(dict)
        date_by_transaction: dict[UUID, date] = {}
        for leg in legs:
            legs_by_transaction[leg.transaction_id][leg.currency_id] = leg.amount
            date_by_transaction[leg.transaction_id] = leg.occurred_at.date()

        samples_by_date: dict[date, list[Decimal]] = defaultdict(list)
        for transaction_id, amounts in legs_by_transaction.items():
            if base.id in amounts and rub.id in amounts:
                samples_by_date[date_by_transaction[transaction_id]].append(amounts[rub.id] / amounts[base.id])

        points = tuple(
            ExchangeRatePoint(
                date=point_date,
                rate=(sum(samples, Decimal("0")) / len(samples)).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP),
            )
            for point_date, samples in sorted(samples_by_date.items())
        )
        return ExchangeRateHistory(base.id, rub.id, points)
