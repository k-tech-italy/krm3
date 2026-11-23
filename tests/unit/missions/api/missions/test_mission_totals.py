"""The mission page shows the expense totals in the base currency."""

from decimal import Decimal

import pytest
from rest_framework.reverse import reverse
from testutils.factories import ExpenseFactory, MissionFactory, PaymentCategoryFactory

from krm3.core.models import Expense


@pytest.fixture
def mission_with_expenses():
    mission = MissionFactory()
    personal = PaymentCategoryFactory(personal_expense=True)
    company = PaymentCategoryFactory(personal_expense=False)
    for payment_type, amount_base, amount_reimbursement in [
        (personal, '100.00', '100.00'),  # personal, with receipt: refunded
        (personal, '40.00', '0.00'),  # personal, no receipt: not refunded yet
        (personal, '15.00', None),  # personal, reimbursement not calculated yet
        (company, '200.00', '0.00'),  # company, with receipt
        (company, '30.00', '-30.00'),  # company, no receipt: to be returned
        (company, None, None),  # company, rate not available yet
    ]:
        expense = ExpenseFactory(mission=mission, payment_type=payment_type)
        # bypass save(), which would calculate the missing amounts
        Expense.objects.filter(pk=expense.pk).update(
            amount_base=amount_base and Decimal(amount_base),
            amount_reimbursement=amount_reimbursement and Decimal(amount_reimbursement),
        )
    return mission


@pytest.mark.django_db
def test_expense_totals(mission_with_expenses):
    assert mission_with_expenses.expense_totals() == {
        'refund': Decimal('70.00'),
        'anticipated': Decimal('230.00'),
        'total': Decimal('330.00'),
    }


@pytest.mark.django_db
def test_expense_totals_without_expenses():
    assert MissionFactory().expense_totals() == {'refund': 0, 'anticipated': 0, 'total': 0}


@pytest.mark.django_db
def test_mission_detail_exposes_totals(api_client, admin_user, mission_with_expenses):
    response = api_client(user=admin_user).get(reverse('missions-api:mission-detail', args=[mission_with_expenses.pk]))

    assert response.status_code == 200
    assert response.json()['totals'] == {'refund': '70.00', 'anticipated': '230.00', 'total': '330.00'}
