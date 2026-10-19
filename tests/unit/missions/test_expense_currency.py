"""A blank Expense.currency is resolved at runtime (#670).

Order: the expense currency, else the mission default_currency, else settings.BASE_CURRENCY.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib import admin
from rest_framework.reverse import reverse
from testutils.factories import (
    DocumentTypeFactory,
    ExpenseCategoryFactory,
    ExpenseFactory,
    MissionFactory,
    PaymentCategoryFactory,
)

from krm3.core.models import Expense
from krm3.currencies.models import Currency
from krm3.missions.forms import ExpenseAdminForm
from krm3.missions.tables import MissionExpenseTable


@pytest.mark.parametrize(
    ('expense_currency', 'mission_currency', 'expected'),
    [
        pytest.param('USD', 'GBP', 'USD', id='own-currency'),
        pytest.param(None, 'GBP', 'GBP', id='mission-default'),
        pytest.param(None, None, 'EUR', id='base-currency'),
    ],
)
def test_get_currency_iso3(db, expense_currency, mission_currency, expected):
    mission = MissionFactory(default_currency=Currency.objects.get(pk=mission_currency) if mission_currency else None)
    expense = ExpenseFactory.build(
        mission=mission, currency=Currency.objects.get(pk=expense_currency) if expense_currency else None
    )

    assert expense.get_currency_iso3() == expected


def test_blank_currency_is_saved_blank_and_converted_with_mission_default(db, monkeypatch):
    rate = MagicMock()
    rate.convert.return_value = Decimal('12.34')
    monkeypatch.setattr('krm3.core.models.missions.Rate.for_date', lambda *a, **kw: rate)
    mission = MissionFactory(default_currency=Currency.objects.get(pk='GBP'))

    expense = ExpenseFactory(mission=mission, currency=None, amount_currency=Decimal('10.00'), amount_base=None)

    expense.refresh_from_db()
    assert expense.currency_id is None
    assert expense.amount_base == Decimal('12.34')
    rate.convert.assert_called_with(Decimal('10.00'), 'GBP')


def test_api_create_without_currency(api_client, regular_user, settings):
    from testutils.factories import ResourceFactory  # noqa: PLC0415

    settings.FLAGS = {**settings.FLAGS, 'TRASFERTE_ENABLED': [('boolean', True)]}

    mission = MissionFactory(resource=ResourceFactory(user=regular_user), default_currency=None)
    payload = {
        'mission': mission.pk,
        'day': mission.from_date.isoformat(),
        'amountCurrency': '10.00',
        'category': ExpenseCategoryFactory().pk,
        'documentType': DocumentTypeFactory().pk,
        'paymentType': PaymentCategoryFactory().pk,
    }

    response = api_client(user=regular_user).post(reverse('missions-api:expense-list'), payload, format='json')

    assert response.status_code == 201, response.data
    expense = Expense.objects.get(mission=mission)
    assert (expense.currency_id, expense.get_currency_iso3(), expense.amount_base) == (None, 'EUR', Decimal('10.00'))


def test_admin_form_keeps_blank_currency(db):
    mission = MissionFactory(default_currency=Currency.objects.get(pk='EUR'))
    data = {
        'mission': mission.pk,
        'day': mission.from_date.isoformat(),
        'amount_currency': '5.00',
        'category': ExpenseCategoryFactory().pk,
        'document_type': DocumentTypeFactory().pk,
        'payment_type': PaymentCategoryFactory().pk,
    }

    form = ExpenseAdminForm(data=data)

    assert form.is_valid(), form.errors
    expense = form.save()
    assert expense.currency_id is None
    assert expense.get_currency_iso3() == 'EUR'


def test_display_uses_resolved_currency(db):
    mission = MissionFactory(default_currency=Currency.objects.get(pk='EUR'))
    expense = ExpenseFactory(mission=mission, currency=None, amount_currency=Decimal('7.00'))

    assert '7.00 EUR' in admin.site._registry[Expense].colored_amount_currency(expense)
    assert '7.00 EUR' in MissionExpenseTable([expense]).render_amount_currency(expense)
