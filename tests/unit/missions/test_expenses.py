from contextlib import nullcontext as does_not_raise
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest
import responses
from django.core.files import File
from django.urls import reverse
from testutils.factories import (
    CurrencyFactory,
    ExpenseFactory,
    MissionFactory,
    PaymentCategoryFactory,
    ReimbursementFactory,
    ResourceFactory,
    SuperUserFactory,
    UserFactory,
)
from testutils.permissions import add_permissions

from krm3.missions.exceptions import AlreadyReimbursed
from krm3.core.models import Expense


def test_expense_manager(expense):
    assert Expense.objects.by_otp(expense.get_otp()) == expense

    expense.id = 0

    with pytest.raises(Expense.DoesNotExist):
        Expense.objects.by_otp(expense.get_otp())


@responses.activate
@pytest.mark.parametrize(
    'iso3, amt_currency, amt_base, expected, force_rates, force_reset',
    [
        pytest.param('EUR', 100.0, None, 100, False, False, id='eur'),
        pytest.param('EUR', 11.0, 100, 100, False, False, id='eur-norecalc'),
        pytest.param('EUR', 11.0, 100, 11, False, True, id='eur-recalc'),
        pytest.param('GBP', 100.0, None, 10, False, False, id='gbp'),
        pytest.param('GBP', 11.0, 100, 100, False, False, id='gbp-norecalc'),
        pytest.param('GBP', 50.0, 100, 5, False, True, id='gbp-recalc'),
    ],
)
def test_expense_calculate_base(iso3, amt_currency, amt_base, expected, force_rates, force_reset, mock_rate_provider):
    mock_rate_provider(day := date(2020, 1, 1), 'EUR,GBP,USD', {'EUR': 0.2, 'GBP': 2, 'USD': 1})

    expense = ExpenseFactory(
        day=day, amount_currency=amt_currency, amount_base=amt_base, currency=CurrencyFactory(iso3=iso3)
    )
    converted = expense.calculate_base(force_rates=force_rates, force_reset=force_reset)
    assert converted == Decimal(expected)


@pytest.mark.parametrize(
    'amt_base, initial, expense_type, image, force, expected',
    [
        pytest.param(100.0, None, 'P', True, False, 100, id='pers-wimage'),
        pytest.param(100.0, None, 'A', True, False, 0, id='az-wimage'),
        pytest.param(100.0, None, 'P', False, False, 0, id='pres-woimage'),
        pytest.param(100.0, None, 'A', False, False, -100, id='az-woimage'),
    ],
)
def test_expense_calculate_reimbursement(amt_base, initial, expense_type, image, force, expected, db, monkeypatch):
    monkeypatch.setattr('krm3.core.models.Expense.calculate_base', Mock())

    if image:
        image = MagicMock(spec=File)
        image.name = 'image.pdf'
    else:
        image = None

    payment_type = PaymentCategoryFactory(personal_expense=expense_type == 'P')
    expense = ExpenseFactory(
        amount_base=amt_base, image=image, payment_type=payment_type, amount_reimbursement=initial, reimbursement=None
    )
    reimbursed = expense.apply_reimbursement(force=force)

    assert reimbursed == Decimal(expected)


def test_expense_already_reimbursed(db):
    expense = ExpenseFactory(reimbursement=ReimbursementFactory())
    with pytest.raises(AlreadyReimbursed):
        expense.apply_reimbursement()


@pytest.mark.parametrize(
    'exp_type, reimbursement, result, expectation',
    [
        pytest.param(True, None, 10, does_not_raise(), id='personal'),
        pytest.param(False, None, 0, does_not_raise(), id='company'),
        pytest.param(False, True, 0, pytest.raises(AlreadyReimbursed), id='reimbursed'),
    ],
)
def test_expense_recalculate_reimbursement_with_image(exp_type, reimbursement, result, expectation, db):
    exp_type = PaymentCategoryFactory(personal_expense=exp_type)
    image = MagicMock(spec=File)
    image.name = 'image.pdf'

    if reimbursement:
        reimbursement = ReimbursementFactory()
    expense: Expense = ExpenseFactory(
        amount_currency=10,
        amount_base=10,
        payment_type=exp_type,
        reimbursement=reimbursement,
        amount_reimbursement=None,
    )

    assert expense.amount_reimbursement is None  # Should be none whe first created
    with expectation:
        expense.image = image
        expense.save()
        expense.refresh_from_db()
        assert expense.amount_reimbursement == result


def test_image_url_returns_none_when_no_file(db):
    expense = ExpenseFactory(image=None)
    assert expense.image_url is None


def test_image_url_returns_authenticated_url_when_file_exists(db):
    image = MagicMock(spec=File)
    image.name = 'receipt.jpg'
    expense = ExpenseFactory(image=image)

    expected_url = reverse('media-auth:expense-image', args=[expense.pk])
    assert expense.image_url == expected_url


def test_accessible_by_superuser_can_access_all_expenses(db):
    """Superuser should have access to all expenses."""
    superuser = SuperUserFactory()
    expense1 = ExpenseFactory()
    expense2 = ExpenseFactory()

    result = Expense.objects.accessible_by(superuser)

    assert expense1 in result
    assert expense2 in result


def test_accessible_by_user_with_view_any_expense_permission(db):
    """User with view_any_expense permission should access all expenses."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.view_any_expense')
    expense1 = ExpenseFactory()
    expense2 = ExpenseFactory()

    result = Expense.objects.accessible_by(user)

    assert expense1 in result
    assert expense2 in result


def test_accessible_by_user_with_manage_any_expense_permission(db):
    """User with manage_any_expense permission should access all expenses."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.manage_any_expense')
    expense1 = ExpenseFactory()
    expense2 = ExpenseFactory()

    result = Expense.objects.accessible_by(user)

    assert expense1 in result
    assert expense2 in result


def test_accessible_by_user_with_matching_resource(db):
    """User can access expenses belonging to missions with their resource."""
    user = UserFactory()
    resource = ResourceFactory(user=user)
    mission = MissionFactory(resource=resource)
    own_expense = ExpenseFactory(mission=mission)
    other_expense = ExpenseFactory()  # Different resource via different mission

    result = Expense.objects.accessible_by(user)

    assert own_expense in result
    assert other_expense not in result


def test_accessible_by_user_without_resource_returns_empty(db):
    """User without an associated resource should get empty queryset."""
    user = UserFactory()
    # User has no resource associated
    expense = ExpenseFactory()

    result = Expense.objects.accessible_by(user)

    assert result.count() == 0
    assert expense not in result


def test_accessible_by_get_resource_exception_returns_empty(db, monkeypatch):
    """When get_resource() raises an exception, should return empty queryset."""
    user = UserFactory()
    expense = ExpenseFactory()

    def raise_exception():
        raise RuntimeError("Database error")

    monkeypatch.setattr(user, 'get_resource', raise_exception)

    result = Expense.objects.accessible_by(user)

    assert result.count() == 0
    assert expense not in result
