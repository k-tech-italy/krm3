"""A blank Expense.currency is stored as the mission default currency, else the base currency (#670)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from testutils.factories import (
    DocumentTypeFactory,
    ExpenseCategoryFactory,
    ExpenseFactory,
    MissionFactory,
    PaymentCategoryFactory,
    ResourceFactory,
)

from krm3.core.models import Expense
from krm3.currencies.models import Currency

CASES = [
    pytest.param('USD', 'GBP', 'USD', id='own-currency'),
    pytest.param(None, 'GBP', 'GBP', id='mission-default'),
    pytest.param(None, None, 'EUR', id='base-currency'),
]


@pytest.fixture(autouse=True)
def fake_rates(monkeypatch):
    """Avoid fetching real exchange rates for non-base currencies."""
    rate = MagicMock()
    rate.convert.side_effect = lambda amount, iso3: amount * 2
    monkeypatch.setattr('krm3.core.models.missions.Rate.for_date', lambda *a, **kw: rate)
    return rate


def _mission(currency):
    return MissionFactory(default_currency=Currency.objects.get(pk=currency) if currency else None)


def _currency(iso3):
    return Currency.objects.get(pk=iso3) if iso3 else None


@pytest.mark.parametrize(('expense_currency', 'mission_currency', 'expected'), CASES)
def test_get_currency_iso3(db, expense_currency, mission_currency, expected):
    expense = ExpenseFactory.build(mission=_mission(mission_currency), currency=_currency(expense_currency))

    assert expense.get_currency_iso3() == expected


@pytest.mark.parametrize(('expense_currency', 'mission_currency', 'expected'), CASES)
def test_save_stores_resolved_currency(db, fake_rates, expense_currency, mission_currency, expected):
    expense = ExpenseFactory(
        mission=_mission(mission_currency),
        currency=_currency(expense_currency),
        amount_currency=Decimal('10.00'),
        amount_base=None,
    )

    expense.refresh_from_db()
    assert expense.currency_id == expected
    if expected == 'EUR':
        assert expense.amount_base == Decimal('10.00')
    else:
        fake_rates.convert.assert_called_with(Decimal('10.00'), expected)
        assert expense.amount_base == Decimal('20.00')


@pytest.mark.parametrize(('expense_currency', 'mission_currency', 'expected'), CASES)
def test_admin_add_stores_resolved_currency(admin_client, expense_currency, mission_currency, expected):
    mission = _mission(mission_currency)
    data = {
        'mission': mission.pk,
        'day': mission.from_date.isoformat(),
        'amount_currency': '5.00',
        'currency': expense_currency or '',
        'category': ExpenseCategoryFactory().pk,
        'document_type': DocumentTypeFactory().pk,
        'payment_type': PaymentCategoryFactory().pk,
    }

    response = admin_client.post(reverse('admin:core_expense_add'), data)

    assert response.status_code == 302
    assert Expense.objects.get(mission=mission).currency_id == expected


@pytest.mark.parametrize(('expense_currency', 'mission_currency', 'expected'), CASES)
def test_api_create_stores_resolved_currency(
    api_client, regular_user, settings, expense_currency, mission_currency, expected
):
    settings.FLAGS = {**settings.FLAGS, 'TRASFERTE_ENABLED': [('boolean', True)]}
    mission = _mission(mission_currency)
    mission.resource = ResourceFactory(user=regular_user)
    mission.save()
    payload = {
        'mission': mission.pk,
        'day': mission.from_date.isoformat(),
        'amountCurrency': '5.00',
        'category': ExpenseCategoryFactory().pk,
        'documentType': DocumentTypeFactory().pk,
        'paymentType': PaymentCategoryFactory().pk,
    }
    if expense_currency:
        payload['currency'] = expense_currency

    response = api_client(user=regular_user).post(reverse('missions-api:expense-list'), payload, format='json')

    assert response.status_code == 201, response.data
    assert Expense.objects.get(mission=mission).currency_id == expected


def test_qr_page_shows_currency(admin_client):
    expense = ExpenseFactory(mission=_mission(None), currency=_currency('GBP'), amount_currency=Decimal('7.00'))

    response = admin_client.get(reverse('admin:core_expense_view_qr', args=[expense.pk]))

    assert response.status_code == 200
    assert 'Amount: 7.00' in response.content.decode()
    assert 'GBP' in response.content.decode()
