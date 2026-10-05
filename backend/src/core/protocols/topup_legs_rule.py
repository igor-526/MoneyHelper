from typing import Protocol
from uuid import UUID


class TopupLegsRule(Protocol):
    def applies(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> bool: ...

    def required_currency_ids(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> frozenset[UUID]: ...
