from decimal import Decimal
from uuid import uuid4

from core.entities import TopupLegRecord
from core.services.rate_averaging import average_rates


def test_averages_single_pair_across_multiple_topups() -> None:
    target_id = uuid4()
    source_id = uuid4()
    transaction_a = uuid4()
    transaction_b = uuid4()
    legs = [
        TopupLegRecord(transaction_id=transaction_a, currency_id=target_id, amount=Decimal("10000")),
        TopupLegRecord(transaction_id=transaction_a, currency_id=source_id, amount=Decimal("780")),
        TopupLegRecord(transaction_id=transaction_b, currency_id=target_id, amount=Decimal("5000")),
        TopupLegRecord(transaction_id=transaction_b, currency_id=source_id, amount=Decimal("400")),
    ]

    rates = average_rates(legs, target_id, {source_id})

    expected = ((Decimal("10000") / Decimal("780")) + (Decimal("5000") / Decimal("400"))) / 2
    assert rates == {source_id: expected}


def test_source_currency_without_matching_topup_is_absent() -> None:
    target_id = uuid4()
    rated_source = uuid4()
    unrated_source = uuid4()
    transaction_id = uuid4()
    legs = [
        TopupLegRecord(transaction_id=transaction_id, currency_id=target_id, amount=Decimal("100")),
        TopupLegRecord(transaction_id=transaction_id, currency_id=rated_source, amount=Decimal("10")),
    ]

    rates = average_rates(legs, target_id, {rated_source, unrated_source})

    assert unrated_source not in rates
    assert rates[rated_source] == Decimal("10")


def test_empty_topup_legs_yield_no_rates() -> None:
    assert average_rates([], uuid4(), {uuid4()}) == {}


def test_topup_without_target_leg_is_ignored() -> None:
    target_id = uuid4()
    source_id = uuid4()
    transaction_id = uuid4()
    legs = [TopupLegRecord(transaction_id=transaction_id, currency_id=source_id, amount=Decimal("10"))]

    assert average_rates(legs, target_id, {source_id}) == {}
