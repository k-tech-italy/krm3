"""The mission detail shows expense amounts with their currency symbol and the totals in the base currency."""

import pytest
from rest_framework.reverse import reverse
from testutils.factories import CurrencyFactory, ExpenseFactory


@pytest.mark.django_db
def test_mission_expenses_expose_currency_symbol(api_client, admin_user):
    expense = ExpenseFactory(currency=CurrencyFactory(iso3='PLN', symbol='zł'))

    response = api_client(user=admin_user).get(reverse('missions-api:mission-detail', args=[expense.mission_id]))

    assert response.status_code == 200
    assert response.json()['expenses'][0]['currencySymbol'] == 'zł'


@pytest.mark.parametrize(
    ('base_currency', 'expected_symbol'),
    [
        pytest.param('EUR', '€', id='base-currency-in-db'),
        pytest.param('XYZ', 'XYZ', id='unknown-base-currency-falls-back-to-iso3'),
    ],
)
@pytest.mark.django_db
def test_user_config_exposes_base_currency(api_client, regular_user, settings, base_currency, expected_symbol):
    CurrencyFactory(iso3='EUR', symbol='€')
    settings.BASE_CURRENCY = base_currency

    response = api_client(user=regular_user).get(reverse('core-api:user-me'))

    assert response.status_code == 200
    assert response.json()['config']['baseCurrency'] == {'iso3': base_currency, 'symbol': expected_symbol}
