import pytest

from app.ledger import Account, AccountClass, Side


@pytest.mark.parametrize(
    ("account_class", "expected_side"),
    [
        (AccountClass.ASSET, Side.DEBIT),
        (AccountClass.EXPENSE, Side.DEBIT),
        (AccountClass.LIABILITY, Side.CREDIT),
        (AccountClass.EQUITY, Side.CREDIT),
        (AccountClass.REVENUE, Side.CREDIT),
    ],
)
def test_account_class_normal_side(account_class, expected_side):
    assert account_class.normal_side is expected_side


def test_account_inherits_normal_side_from_class():
    cash = Account(code="1000", name="Cash", account_class=AccountClass.ASSET)
    revenue = Account(code="4000", name="Sales", account_class=AccountClass.REVENUE)
    assert cash.normal_side is Side.DEBIT
    assert revenue.normal_side is Side.CREDIT


def test_account_rejects_empty_code():
    with pytest.raises(ValueError):
        Account(code="", name="Cash", account_class=AccountClass.ASSET)


def test_account_rejects_empty_name():
    with pytest.raises(ValueError):
        Account(code="1000", name="", account_class=AccountClass.ASSET)


def test_account_rejects_non_enum_class():
    with pytest.raises(TypeError):
        Account(code="1000", name="Cash", account_class="asset")  # type: ignore[arg-type]
