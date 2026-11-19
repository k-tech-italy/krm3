import decimal
import warnings

import pytest
from django.contrib.admin import site
from django.utils.deprecation import RemovedInDjango60Warning
from testutils.factories import ExpenseFactory, MissionFactory

from krm3.core.models import Expense


@pytest.fixture
def expense_admin():
    return site._registry[Expense]


@pytest.mark.parametrize(
    ('status', 'expected'),
    [
        pytest.param('SUBMITTED', 'Rome &lt;b&gt;', id='submitted-plain'),
        pytest.param('DRAFT', '<span style="color: grey;">', id='draft-grey'),
        pytest.param('CANCELLED', 'line-through', id='cancelled-struck'),
    ],
)
def test_mission_column_escapes_title(db, expense_admin, status, expected):
    number = None if status == 'DRAFT' else 1
    expense = ExpenseFactory(mission=MissionFactory(status=status, number=number, title='Rome <b>'))

    with warnings.catch_warnings():
        warnings.simplefilter('error', RemovedInDjango60Warning)
        html = expense_admin.mission_st(expense)

    assert expected in html
    assert '<b>' not in html


def test_negative_amounts_are_red(db, expense_admin):
    expense = ExpenseFactory(amount_base=decimal.Decimal(-10), amount_reimbursement=decimal.Decimal(-5))

    with warnings.catch_warnings():
        warnings.simplefilter('error', RemovedInDjango60Warning)
        base = expense_admin.colored_amount_base(expense)
        reimbursement = expense_admin.colored_amount_reimbursement(expense)
        currency = expense_admin.colored_amount_currency(expense)

    assert base == '<span style="color: red;">-10</span>'
    assert reimbursement == '<span style="color: red;">5</span>'
    assert expense.currency.iso3 in currency
