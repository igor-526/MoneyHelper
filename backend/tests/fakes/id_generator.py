from uuid import UUID


class SequentialIdGenerator:
    """Детерминированные UUID: 00000000-0000-0000-0000-000000000001, ...002 и т. д."""

    def __init__(self, start: int = 1) -> None:
        self._counter = start

    def new(self) -> UUID:
        value = UUID(int=self._counter)
        self._counter += 1
        return value
