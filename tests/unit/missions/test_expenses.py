import pytest

from krm3.missions.models import Expense


def test_expense_manager(expense):
    assert Expense.objects.by_otp(expense.get_otp()) == expense

    expense.id = 0

    with pytest.raises(Expense.DoesNotExist):
        Expense.objects.by_otp(expense.get_otp())
