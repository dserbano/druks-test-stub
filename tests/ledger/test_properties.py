from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

from app.ledger import (
    Account,
    AccountClass,
    Journal,
    JournalEntry,
    JournalLine,
    Money,
    Side,
    UnbalancedEntryError,
    trial_balance,
)


ACCOUNTS = [
    Account(code=f"{1000 + i}", name=f"Acct {i}", account_class=cls)
    for i, cls in enumerate(
        [
            AccountClass.ASSET,
            AccountClass.LIABILITY,
            AccountClass.EQUITY,
            AccountClass.REVENUE,
            AccountClass.EXPENSE,
            AccountClass.ASSET,
        ]
    )
]

positive_decimals = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)


@st.composite
def balanced_entries(draw):
    """Draw N positive debit amounts, mirror each to a credit against another account.

    By construction the entry is single-currency and sums to zero.
    """
    currency = draw(st.sampled_from(["USD", "EUR", "GBP"]))
    n = draw(st.integers(min_value=1, max_value=4))
    amounts = draw(st.lists(positive_decimals, min_size=n, max_size=n))
    debit_accounts = draw(st.lists(st.sampled_from(ACCOUNTS), min_size=n, max_size=n))
    credit_accounts = draw(st.lists(st.sampled_from(ACCOUNTS), min_size=n, max_size=n))
    lines = []
    for account, amount in zip(debit_accounts, amounts):
        lines.append(
            JournalLine(account=account, side=Side.DEBIT, amount=Money(amount, currency))
        )
    for account, amount in zip(credit_accounts, amounts):
        lines.append(
            JournalLine(account=account, side=Side.CREDIT, amount=Money(amount, currency))
        )
    return JournalEntry(
        entry_date=date(2026, 1, 1), memo=draw(st.text(max_size=20)), lines=tuple(lines)
    )


@given(balanced_entries())
def test_any_balanced_entry_posts(entry):
    journal = Journal()
    journal.post(entry)
    assert len(journal) == 1


@given(st.lists(balanced_entries(), min_size=1, max_size=10))
def test_trial_balance_debits_equal_credits(entries):
    # Hypothesis may mix currencies across entries; keep a single-currency journal.
    currency = entries[0].currency
    entries = [e for e in entries if e.currency == currency]
    journal = Journal()
    for entry in entries:
        journal.post(entry)
    tb = trial_balance(journal)
    assert tb.total_debits == tb.total_credits
    assert tb.is_balanced


@given(
    debit_amount=positive_decimals,
    credit_amount=positive_decimals,
    currency=st.sampled_from(["USD", "EUR"]),
)
def test_unbalanced_entries_rejected(debit_amount, credit_amount, currency):
    if debit_amount == credit_amount:
        return  # not the case under test
    with pytest.raises(UnbalancedEntryError):
        JournalEntry(
            entry_date=date(2026, 1, 1),
            memo="unbalanced",
            lines=(
                JournalLine(
                    account=ACCOUNTS[0],
                    side=Side.DEBIT,
                    amount=Money(debit_amount, currency),
                ),
                JournalLine(
                    account=ACCOUNTS[1],
                    side=Side.CREDIT,
                    amount=Money(credit_amount, currency),
                ),
            ),
        )
