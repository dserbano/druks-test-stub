from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.ledger.accounts import Account, Side
from app.ledger.money import Money


class UnbalancedEntryError(ValueError):
    """Raised when a journal entry's debits and credits do not sum to zero."""


class MixedCurrencyError(ValueError):
    """Raised when a journal entry mixes currencies."""


@dataclass(frozen=True)
class JournalLine:
    account: Account
    side: Side
    amount: Money

    def __post_init__(self) -> None:
        if not isinstance(self.side, Side):
            raise TypeError("JournalLine.side must be a Side")
        if not isinstance(self.amount, Money):
            raise TypeError("JournalLine.amount must be a Money")
        if self.amount.amount <= 0:
            raise ValueError("JournalLine.amount must be strictly positive")

    @property
    def signed_amount(self) -> Decimal:
        """Debit as +amount, credit as -amount (in entry currency units)."""
        return self.amount.amount if self.side is Side.DEBIT else -self.amount.amount


@dataclass(frozen=True)
class JournalEntry:
    entry_date: date
    memo: str
    lines: tuple[JournalLine, ...]

    def __post_init__(self) -> None:
        if not self.lines:
            raise UnbalancedEntryError("journal entry must have at least one line")
        currencies = {line.amount.currency for line in self.lines}
        if len(currencies) != 1:
            raise MixedCurrencyError(
                f"journal entry mixes currencies: {sorted(currencies)!r}"
            )
        total = sum((line.signed_amount for line in self.lines), Decimal(0))
        if total != 0:
            raise UnbalancedEntryError(
                f"journal entry debits and credits do not balance (net={total})"
            )

    @property
    def currency(self) -> str:
        return self.lines[0].amount.currency


@dataclass
class Journal:
    entries: list[JournalEntry] = field(default_factory=list)

    def post(self, entry: JournalEntry) -> JournalEntry:
        """Append ``entry`` to the journal.

        Posting a :class:`JournalEntry` is a no-op beyond recording it — the entry's
        balance invariants are enforced at construction time, so an unbalanced or
        mixed-currency entry raises before it ever reaches ``post``. Accepting a
        prebuilt :class:`JournalEntry` keeps the validation path and the posting
        path from drifting.
        """
        if not isinstance(entry, JournalEntry):
            raise TypeError("Journal.post expects a JournalEntry")
        self.entries.append(entry)
        return entry

    def post_lines(
        self,
        entry_date: date,
        memo: str,
        lines: Iterable[JournalLine],
    ) -> JournalEntry:
        """Build a :class:`JournalEntry` from ``lines`` and post it.

        Raises :class:`UnbalancedEntryError` or :class:`MixedCurrencyError` without
        appending anything when the lines do not sum to zero in a single currency.
        """
        entry = JournalEntry(entry_date=entry_date, memo=memo, lines=tuple(lines))
        return self.post(entry)

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)
