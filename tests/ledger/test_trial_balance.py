from datetime import date
from decimal import Decimal

import pytest

from app.ledger import (
    Account,
    AccountClass,
    Journal,
    JournalLine,
    MixedCurrencyError,
    Money,
    Side,
    trial_balance,
)


CASH = Account(code="1000", name="Cash", account_class=AccountClass.ASSET)
AR = Account(code="1100", name="Accounts Receivable", account_class=AccountClass.ASSET)
REVENUE = Account(code="4000", name="Sales", account_class=AccountClass.REVENUE)
RENT = Account(code="5000", name="Rent", account_class=AccountClass.EXPENSE)


def _usd(amount: str) -> Money:
    return Money(Decimal(amount), "USD")


def test_empty_journal_has_zero_totals():
    tb = trial_balance(Journal())
    assert tb.total_debits == Decimal(0)
    assert tb.total_credits == Decimal(0)
    assert tb.is_balanced


def test_totals_equal_over_non_trivial_journal():
    journal = Journal()
    journal.post_lines(
        entry_date=date(2026, 1, 1),
        memo="cash sale",
        lines=[
            JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("250.00")),
            JournalLine(account=REVENUE, side=Side.CREDIT, amount=_usd("250.00")),
        ],
    )
    journal.post_lines(
        entry_date=date(2026, 1, 2),
        memo="credit sale",
        lines=[
            JournalLine(account=AR, side=Side.DEBIT, amount=_usd("400.00")),
            JournalLine(account=REVENUE, side=Side.CREDIT, amount=_usd("400.00")),
        ],
    )
    journal.post_lines(
        entry_date=date(2026, 1, 3),
        memo="pay rent",
        lines=[
            JournalLine(account=RENT, side=Side.DEBIT, amount=_usd("120.00")),
            JournalLine(account=CASH, side=Side.CREDIT, amount=_usd("120.00")),
        ],
    )

    tb = trial_balance(journal)

    assert tb.currency == "USD"
    assert tb.total_debits == tb.total_credits
    assert tb.total_debits == Decimal("770.00")
    assert tb.is_balanced

    assert tb.by_account[CASH].debit == Decimal("250.00")
    assert tb.by_account[CASH].credit == Decimal("120.00")
    assert tb.by_account[CASH].balance == Decimal("130.00")
    assert tb.by_account[AR].debit == Decimal("400.00")
    assert tb.by_account[AR].credit == Decimal(0)
    assert tb.by_account[REVENUE].credit == Decimal("650.00")
    assert tb.by_account[REVENUE].debit == Decimal(0)
    assert tb.by_account[RENT].debit == Decimal("120.00")


def test_mixed_currency_journal_rejected():
    journal = Journal()
    journal.post_lines(
        entry_date=date(2026, 1, 1),
        memo="usd",
        lines=[
            JournalLine(account=CASH, side=Side.DEBIT, amount=Money(Decimal("10"), "USD")),
            JournalLine(account=REVENUE, side=Side.CREDIT, amount=Money(Decimal("10"), "USD")),
        ],
    )
    journal.post_lines(
        entry_date=date(2026, 1, 2),
        memo="eur",
        lines=[
            JournalLine(account=CASH, side=Side.DEBIT, amount=Money(Decimal("10"), "EUR")),
            JournalLine(account=REVENUE, side=Side.CREDIT, amount=Money(Decimal("10"), "EUR")),
        ],
    )
    with pytest.raises(MixedCurrencyError):
        trial_balance(journal)
