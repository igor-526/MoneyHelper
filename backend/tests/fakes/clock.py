from datetime import UTC, datetime, timedelta


class FixedClock:
    def __init__(self, moment: datetime | None = None) -> None:
        self._moment = moment or datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._moment

    def advance(self, delta: timedelta) -> None:
        self._moment += delta


class FixedOperationClock(FixedClock):
    def __init__(self, moment: datetime | None = None) -> None:
        super().__init__(moment or datetime(2026, 1, 1))
