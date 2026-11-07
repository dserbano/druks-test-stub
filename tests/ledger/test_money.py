from decimal import Decimal

import pytest

from app.ledger import Money


def test_money_requires_decimal_amount():
    with pytest.raises(TypeError):
        Money(1.0, "USD")  # type: ignore[arg-type]


def test_money_requires_non_empty_currency():
    with pytest.raises(ValueError):
        Money(Decimal("1"), "")


def test_money_addition_same_currency():
    assert Money(Decimal("1.25"), "USD") + Money(Decimal("2.75"), "USD") == Money(
        Decimal("4.00"), "USD"
    )


def test_money_addition_mixed_currency_rejected():
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")


def test_money_negation():
    assert -Money(Decimal("5"), "USD") == Money(Decimal("-5"), "USD")
