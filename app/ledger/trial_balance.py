from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.ledger.accounts import Account, Side
from app.ledger.journal import Journal, MixedCurrencyError


@dataclass(frozen=True)
class AccountTotals:
    debit: Decimal
    credit: Decimal

    @property
    def balance(self) -> Decimal:
        """Debit minus credit; positive is a net debit balance."""
        return self.debit - self.credit


@dataclass(frozen=True)
class TrialBalance:
    currency: str
    by_account: dict[Account, AccountTotals]
    total_debits: Decimal
    total_credits: Decimal

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits


def trial_balance(journal: Journal) -> TrialBalance:
    """Compute per-account debit/credit totals across every posted entry.

    Every :class:`~app.ledger.journal.JournalEntry` is single-currency and the
    trial balance of a mixed-currency journal is ill-defined without an FX layer
    (deferred), so this function raises :class:`MixedCurrencyError` when entries
    span more than one currency.
    """
    if not journal.entries:
        return TrialBalance(
            currency="",
            by_account={},
            total_debits=Decimal(0),
            total_credits=Decimal(0),
        )

    currencies = {entry.currency for entry in journal.entries}
    if len(currencies) != 1:
        raise MixedCurrencyError(
            f"trial_balance requires a single currency; saw {sorted(currencies)!r}"
        )
    currency = next(iter(currencies))

    debits: dict[Account, Decimal] = {}
    credits: dict[Account, Decimal] = {}
    for entry in journal.entries:
        for line in entry.lines:
            bucket = debits if line.side is Side.DEBIT else credits
            bucket[line.account] = bucket.get(line.account, Decimal(0)) + line.amount.amount

    accounts = set(debits) | set(credits)
    by_account = {
        account: AccountTotals(
            debit=debits.get(account, Decimal(0)),
            credit=credits.get(account, Decimal(0)),
        )
        for account in accounts
    }
    total_debits = sum(debits.values(), Decimal(0))
    total_credits = sum(credits.values(), Decimal(0))
    return TrialBalance(
        currency=currency,
        by_account=by_account,
        total_debits=total_debits,
        total_credits=total_credits,
    )
