from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.entities import DatedTopupLegRecord


class ExchangeRateHistoryReader(Protocol):
    async def list_dated_topup_legs(
        self,
        workspace_id: UUID,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[DatedTopupLegRecord]: ...
