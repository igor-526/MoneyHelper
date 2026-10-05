from uuid import UUID


class SameCurrencyTopupLegs:
    def applies(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> bool:
        return workspace_currency_id == wallet_currency_id

    def required_currency_ids(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> frozenset[UUID]:
        return frozenset({wallet_currency_id})


class CrossCurrencyTopupLegs:
    def applies(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> bool:
        return workspace_currency_id != wallet_currency_id

    def required_currency_ids(self, workspace_currency_id: UUID, wallet_currency_id: UUID) -> frozenset[UUID]:
        return frozenset({workspace_currency_id, wallet_currency_id})
