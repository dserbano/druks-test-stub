from datetime import date
from decimal import Decimal

import pytest

from app.ledger import (
    Account,
    AccountClass,
    Journal,
    JournalEntry,
    JournalLine,
    MixedCurrencyError,
    Money,
    Side,
    UnbalancedEntryError,
)


CASH = Account(code="1000", name="Cash", account_class=AccountClass.ASSET)
REVENUE = Account(code="4000", name="Sales", account_class=AccountClass.REVENUE)
EXPENSE = Account(code="5000", name="Rent", account_class=AccountClass.EXPENSE)


def _usd(amount: str) -> Money:
    return Money(Decimal(amount), "USD")


def test_balanced_entry_posts():
    journal = Journal()
    entry = journal.post_lines(
        entry_date=date(2026, 1, 1),
        memo="cash sale",
        lines=[
            JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("100")),
            JournalLine(account=REVENUE, side=Side.CREDIT, amount=_usd("100")),
        ],
    )
    assert isinstance(entry, JournalEntry)
    assert len(journal) == 1
    assert list(journal)[0] is entry


def test_unbalanced_entry_rejected_and_not_posted():
    journal = Journal()
    with pytest.raises(UnbalancedEntryError):
        journal.post_lines(
            entry_date=date(2026, 1, 1),
            memo="broken",
            lines=[
                JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("100")),
                JournalLine(account=REVENUE, side=Side.CREDIT, amount=_usd("90")),
            ],
        )
    assert len(journal) == 0


def test_mixed_currency_entry_rejected():
    with pytest.raises(MixedCurrencyError):
        JournalEntry(
            entry_date=date(2026, 1, 1),
            memo="mixed",
            lines=(
                JournalLine(account=CASH, side=Side.DEBIT, amount=Money(Decimal("1"), "USD")),
                JournalLine(account=REVENUE, side=Side.CREDIT, amount=Money(Decimal("1"), "EUR")),
            ),
        )


def test_empty_entry_rejected():
    with pytest.raises(UnbalancedEntryError):
        JournalEntry(entry_date=date(2026, 1, 1), memo="empty", lines=())


def test_line_amount_must_be_positive():
    with pytest.raises(ValueError):
        JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("0"))
    with pytest.raises(ValueError):
        JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("-1"))


def test_signed_amount_follows_side():
    debit = JournalLine(account=CASH, side=Side.DEBIT, amount=_usd("10"))
    credit = JournalLine(account=REVENUE, side=Side.CREDIT, amount=_usd("10"))
    assert debit.signed_amount == Decimal("10")
    assert credit.signed_amount == Decimal("-10")


def test_multi_line_balanced_entry_with_split_debits():
    journal = Journal()
    journal.post_lines(
        entry_date=date(2026, 1, 1),
        memo="split expense",
        lines=[
            JournalLine(account=EXPENSE, side=Side.DEBIT, amount=_usd("40")),
            JournalLine(account=EXPENSE, side=Side.DEBIT, amount=_usd("60")),
            JournalLine(account=CASH, side=Side.CREDIT, amount=_usd("100")),
        ],
    )
    assert len(journal) == 1


def test_post_rejects_non_entry():
    journal = Journal()
    with pytest.raises(TypeError):
        journal.post("not an entry")  # type: ignore[arg-type]
