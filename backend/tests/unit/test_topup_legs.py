from uuid import uuid4

from core.services.topup_legs import CrossCurrencyTopupLegs, SameCurrencyTopupLegs

WORKSPACE_CURRENCY = uuid4()
OTHER_CURRENCY = uuid4()


def test_same_currency_rule_applies_when_currencies_match() -> None:
    rule = SameCurrencyTopupLegs()

    assert rule.applies(WORKSPACE_CURRENCY, WORKSPACE_CURRENCY)
    assert not rule.applies(WORKSPACE_CURRENCY, OTHER_CURRENCY)


def test_same_currency_rule_requires_single_currency() -> None:
    rule = SameCurrencyTopupLegs()

    assert rule.required_currency_ids(WORKSPACE_CURRENCY, WORKSPACE_CURRENCY) == {WORKSPACE_CURRENCY}


def test_cross_currency_rule_applies_when_currencies_differ() -> None:
    rule = CrossCurrencyTopupLegs()

    assert rule.applies(WORKSPACE_CURRENCY, OTHER_CURRENCY)
    assert not rule.applies(WORKSPACE_CURRENCY, WORKSPACE_CURRENCY)


def test_cross_currency_rule_requires_both_currencies() -> None:
    rule = CrossCurrencyTopupLegs()

    assert rule.required_currency_ids(WORKSPACE_CURRENCY, OTHER_CURRENCY) == {WORKSPACE_CURRENCY, OTHER_CURRENCY}
