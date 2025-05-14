from contextlib import nullcontext as does_not_raise
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest
import responses
from django.core.files import File
from testutils.factories import CurrencyFactory, ExpenseFactory, PaymentCategoryFactory, ReimbursementFactory

from krm3.missions.exceptions import AlreadyReimbursed
from krm3.core.models import Expense


def test_expense_manager(expense):
    assert Expense.objects.by_otp(expense.get_otp()) == expense

    expense.id = 0

    with pytest.raises(Expense.DoesNotExist):
        Expense.objects.by_otp(expense.get_otp())


@responses.activate
@pytest.mark.parametrize(
    'iso3, amt_currency, amt_base, expected, force_rates, force_reset', [
        pytest.param('EUR', 100.0, None, 100, False, False, id='eur'),
        pytest.param('EUR', 11.0, 100, 100, False, False, id='eur-norecalc'),
        pytest.param('EUR', 11.0, 100, 11, False, True, id='eur-recalc'),
        pytest.param('GBP', 100.0, None, 10, False, False, id='gbp'),
        pytest.param('GBP', 11.0, 100, 100, False, False, id='gbp-norecalc'),
        pytest.param('GBP', 50.0, 100, 5, False, True, id='gbp-recalc'),
    ]
)
def test_expense_calculate_base(iso3, amt_currency, amt_base, expected, force_rates, force_reset, mock_rate_provider):
    mock_rate_provider(day := date(2020, 1, 1), 'EUR,GBP,USD', {'EUR': 0.2, 'GBP': 2, 'USD': 1})

    expense = ExpenseFactory(day=day, amount_currency=amt_currency, amount_base=amt_base,
                             currency=CurrencyFactory(iso3=iso3))
    converted = expense.calculate_base(force_rates=force_rates, force_reset=force_reset)
    assert converted == Decimal(expected)


@pytest.mark.parametrize(
    'amt_base, initial, expense_type, image, force, expected', [
        pytest.param(100.0, None, 'P', True, False, 100, id='pers-wimage'),
        pytest.param(100.0, None, 'A', True, False, 0, id='az-wimage'),
        pytest.param(100.0, None, 'P', False, False, 0, id='pres-woimage'),
        pytest.param(100.0, None, 'A', False, False, -100, id='az-woimage'),
    ]
)
def test_expense_calculate_reimbursement(amt_base, initial, expense_type, image, force, expected, db, monkeypatch):
    monkeypatch.setattr('krm3.core.models.Expense.calculate_base', Mock())

    if image:
        image = MagicMock(spec=File)
        image.name = 'image.pdf'
    else:
        image = None

    payment_type = PaymentCategoryFactory(personal_expense=expense_type == 'P')
    expense = ExpenseFactory(amount_base=amt_base, image=image, payment_type=payment_type,
                             amount_reimbursement=initial, reimbursement=None)
    reimbursed = expense.apply_reimbursement(force=force)

    assert reimbursed == Decimal(expected)


def test_expense_already_reimbursed(db):
    expense = ExpenseFactory(reimbursement=ReimbursementFactory())
    with pytest.raises(AlreadyReimbursed):
        expense.apply_reimbursement()


@pytest.mark.parametrize(
    'exp_type, reimbursement, result, expectation', [
        pytest.param(True, None, 10, does_not_raise(), id='personal'),
        pytest.param(False, None, 0, does_not_raise(), id='company'),
        pytest.param(False, True, 0, pytest.raises(AlreadyReimbursed), id='reimbursed'),
    ]
)
def test_expense_recalculate_reimbursement_with_image(exp_type, reimbursement, result, expectation, db):
    exp_type = PaymentCategoryFactory(personal_expense=exp_type)
    image = MagicMock(spec=File)
    image.name = 'image.pdf'

    if reimbursement:
        reimbursement = ReimbursementFactory()
    expense: Expense = ExpenseFactory(
        amount_currency=10, amount_base=10, payment_type=exp_type,
        reimbursement=reimbursement, amount_reimbursement=None,
    )

    assert expense.amount_reimbursement is None  # Should be none whe first created
    with expectation:
        expense.image = image
        expense.save()
        expense.refresh_from_db()
        assert expense.amount_reimbursement == result
