from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from core.entities import TopupLegRecord


def average_rates(topup_legs: Sequence[TopupLegRecord], target_id: UUID, source_ids: set[UUID]) -> dict[UUID, Decimal]:
    legs_by_transaction: dict[UUID, dict[UUID, Decimal]] = defaultdict(dict)
    for leg in topup_legs:
        legs_by_transaction[leg.transaction_id][leg.currency_id] = leg.amount
    samples: dict[UUID, list[Decimal]] = defaultdict(list)
    for legs_map in legs_by_transaction.values():
        if target_id not in legs_map:
            continue
        for source_id in source_ids:
            if source_id in legs_map:
                samples[source_id].append(legs_map[target_id] / legs_map[source_id])
    return {source_id: sum(values, Decimal("0")) / len(values) for source_id, values in samples.items()}
