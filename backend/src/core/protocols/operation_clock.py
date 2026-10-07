from datetime import datetime
from typing import Protocol


class OperationClock(Protocol):
    def now(self) -> datetime:
        """Текущее локальное время операции без часового пояса."""
