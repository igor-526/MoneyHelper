from typing import Protocol
from uuid import UUID


class WorkspaceCurrencyReader(Protocol):
    async def get_currency_id(self, workspace_id: UUID) -> UUID | None: ...
