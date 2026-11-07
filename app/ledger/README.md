# app/ledger

A minimal double-entry accounting slice: **chart of accounts**, **journal entries**, and
**trial balance**. Designed so later sibling tickets (FX, income statement, balance sheet,
cash-flow statement, period close, audit log, CLI) extend this surface rather than rewrite it.

## Public API

```python
from app.ledger import (
    Account,
    AccountClass,
    Side,
    Money,
    JournalLine,
    JournalEntry,
    Journal,
    UnbalancedEntryError,
    MixedCurrencyError,
    trial_balance,
    TrialBalance,
)
```

### Chart of accounts

`AccountClass` enumerates the five classical account classes — `ASSET`, `LIABILITY`,
`EQUITY`, `REVENUE`, `EXPENSE` — and exposes each class's `normal_side` (`Side.DEBIT` for
assets and expenses, `Side.CREDIT` for liabilities, equity, and revenue). An `Account` pairs
a `code`, `name`, and `AccountClass`.

### Journal entries

A `JournalEntry` is a dated, memo'd tuple of `JournalLine`s, each a `(account, side, amount)`
triple. Construction validates that every entry is **single-currency** and that its debits
and credits **sum to zero** — unbalanced entries raise `UnbalancedEntryError` and
mixed-currency entries raise `MixedCurrencyError`. A `Journal` holds the posted entries;
`Journal.post` appends an already-validated entry, and `Journal.post_lines` builds and posts
one in a single step.

### Trial balance

`trial_balance(journal)` returns a `TrialBalance` with per-account debit/credit totals and
aggregate `total_debits` / `total_credits`. The ledger's core invariant — total debits equal
total credits over any posted journal — is exposed as `TrialBalance.is_balanced`.

## Money rule

Monetary amounts in `app/ledger/` are `Money(amount: decimal.Decimal, currency: str)`. **No
`float` is used for money** anywhere in the slice: floats silently lose cents on rounding and
would make the deferred FX sibling ticket a rewrite rather than an extension. The explicit
`currency` tag is the hook the FX layer will build on; this slice refuses to mix currencies
inside an entry or a trial balance.

## Not in this slice

Income statement, balance sheet, cash-flow statement, FX / exchange rates, period closing,
audit log, and the CLI are deferred to sibling tickets.
