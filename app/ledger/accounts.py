from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class AccountClass(Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"

    @property
    def normal_side(self) -> Side:
        if self in (AccountClass.ASSET, AccountClass.EXPENSE):
            return Side.DEBIT
        return Side.CREDIT


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    account_class: AccountClass

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Account.code must be non-empty")
        if not self.name:
            raise ValueError("Account.name must be non-empty")
        if not isinstance(self.account_class, AccountClass):
            raise TypeError("Account.account_class must be an AccountClass")

    @property
    def normal_side(self) -> Side:
        return self.account_class.normal_side
