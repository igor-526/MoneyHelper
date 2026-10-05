from datetime import date, tzinfo
from typing import Protocol
from uuid import UUID

from core.entities import LegRecord


class AnalyticsDimension(Protocol):
    def key(self, record: LegRecord, tz: tzinfo) -> UUID | date: ...
