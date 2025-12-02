import sys
import typing
from pathlib import Path
from typing import cast

import pytest
import responses
from rest_framework.test import APIClient

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource


def pytest_configure(config):
    here = Path(__file__).parent
    sys.path.insert(0, str(here / '_extras'))


@pytest.fixture
def krm3app(django_app_factory):
    return django_app_factory(csrf_checks=False)


@pytest.fixture(autouse=True)
def session_settings(settings):
    # Ensure session cookies work in test environment (HTTP, not HTTPS)
    settings.SESSION_COOKIE_SECURE = False
    settings.DEBUG = False


@pytest.fixture(autouse=True)
def dummy_currencies(settings):
    settings.CURRENCIES = ['GBP', 'EUR', 'USD']
    settings.OPEN_EXCHANGE_RATES_APP_ID = 'abc'
    settings.BASE_CURRENCY = 'EUR'


@pytest.fixture(autouse=True)
def currencies(db):
    from krm3.currencies.models import Currency

    Currency.objects.get_or_create(
        iso3='GBP',
        defaults={'title': 'GBP', 'symbol': '£', 'fractional_unit': 'cents', 'base': 100, 'active': True},
    )
    Currency.objects.get_or_create(
        iso3='EUR',
        defaults={'title': 'EUR', 'symbol': '€', 'fractional_unit': 'cents', 'base': 100, 'active': True},
    )
    Currency.objects.get_or_create(
        iso3='USD',
        defaults={'title': 'USD', 'symbol': '$', 'fractional_unit': 'cents', 'base': 100, 'active': True},
    )
    Currency.objects.get_or_create(
        iso3='CHF',
        defaults={'title': 'CHF', 'symbol': 'CHF', 'fractional_unit': 'cents', 'base': 100, 'active': True},
    )


@pytest.fixture
def mock_rate_provider(settings, db):
    from django.utils.http import urlencode

    def fx(day, requested, retrieved):
        responses.add(
            responses.GET,
            f'https://openexchangerates.org/api/historical/{day:%Y-%m-%d}.json?'
            + urlencode({'app_id': settings.OPEN_EXCHANGE_RATES_APP_ID, 'symbols': requested}),
            json={
                'disclaimer': 'Usage subject to terms: https://openexchangerates.org/terms',
                'license': 'https://openexchangerates.org/license',
                'timestamp': 1582588799,
                'base': 'USD',
                'rates': retrieved,
            },
            status=200,
        )

    return fx


@pytest.fixture
def regular_user(db):
    from testutils.factories import UserFactory

    return UserFactory()


@pytest.fixture
def staff_user(db):
    from testutils.factories import UserFactory

    return UserFactory(is_staff=True)


# This admin_user_with_plain_password has the _password attribute set (plaintext),
# unlike the default Django fixture admin_user.
# Useful for Selenium login where the raw password is needed.
@pytest.fixture
def admin_user_with_plain_password(db):
    from testutils.factories import UserFactory

    return UserFactory(is_superuser=True, is_staff=True)


@pytest.fixture
def payment_types(db):
    results = []
    from krm3.core.models import PaymentCategory

    azienda = PaymentCategory.objects.create(title='Azienda')
    results.append(PaymentCategory.objects.create(title='Anticipo', parent=azienda))
    results.append(PaymentCategory.objects.create(title='CCA', parent=azienda))
    personale = PaymentCategory.objects.create(title='Personale')
    results.append(PaymentCategory.objects.create(title='CCP', parent=personale))
    results.append(PaymentCategory.objects.create(title='Cash', parent=personale))
    return results


@pytest.fixture
def document_types(db):
    results = []
    from krm3.core.models import DocumentType

    results.append(DocumentType.objects.get_or_create(title='Scontrino', default=True)[0])
    results.append(DocumentType.objects.get_or_create(title='Fattura')[0])
    results.append(DocumentType.objects.get_or_create(title='Altro')[0])
    results.append(DocumentType.objects.get_or_create(title='Disabled', active=False)[0])
    return results


@pytest.fixture
def categories(db):
    from testutils.factories import ExpenseCategoryFactory, PaymentCategoryFactory

    expenses = {
        'alloggio': ExpenseCategoryFactory(title='Alloggio'),
        'forfait': ExpenseCategoryFactory(title='Forfait'),
        'rappresentanza': ExpenseCategoryFactory(title='Rappresentanza'),
        'vitto': ExpenseCategoryFactory(title='Vitto'),
        'viaggio': ExpenseCategoryFactory(title='Viaggio'),
    }

    expenses.update(
        {
            'viaggio.taxi': ExpenseCategoryFactory(title='Taxi', parent=expenses['viaggio']),
            'viaggio.train': ExpenseCategoryFactory(title='Train', parent=expenses['viaggio']),
            'vitto.pranzo': ExpenseCategoryFactory(title='Pranzo', parent=expenses['vitto']),
            'vitto.cena': ExpenseCategoryFactory(title='Cena', parent=expenses['vitto']),
            'forfait.alloggio': ExpenseCategoryFactory(title='Alloggio', parent=expenses['forfait']),
            'forfait.vitto': ExpenseCategoryFactory(title='Vitto', parent=expenses['forfait']),
            'forfait.aereo': ExpenseCategoryFactory(title='Aereo', parent=expenses['forfait']),
            'forfait.treno': ExpenseCategoryFactory(title='Treno', parent=expenses['forfait']),
        }
    )

    payments = {
        'personal': PaymentCategoryFactory(title='Personal', personal_expense=True),
        'company': PaymentCategoryFactory(title='Company', personal_expense=False),
    }

    payments.update(
        {
            'company.cca': PaymentCategoryFactory(title='CCA', parent=payments['company']),
            'company.wire': PaymentCategoryFactory(title='Wire', parent=payments['company']),
            'company.forfait': PaymentCategoryFactory(
                title='Forfait', parent=payments['company'], personal_expense=True
            ),
        }
    )

    return type('Categories', (), {'expenses': expenses, 'payments': payments})()


@pytest.fixture
def country(db):
    from testutils.factories import CountryFactory

    return CountryFactory()


@pytest.fixture
def city(db):
    from testutils.factories import CityFactory

    return CityFactory()


@pytest.fixture
def resource(db):
    from testutils.factories import ResourceFactory

    return ResourceFactory()


@pytest.fixture
def resource_factory():
    from testutils.factories import ResourceFactory  # noqa: PLC0415

    def _make(*args, **kwargs):
        return ResourceFactory(*args, **kwargs)

    return _make


@pytest.fixture
def project(db):
    from testutils.factories import ProjectFactory

    return ProjectFactory()


@pytest.fixture
def krm3client(db):
    from testutils.factories import ClientFactory  # noqa: PLC0415

    return ClientFactory()


@pytest.fixture
def api_client():
    def fx(user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user=user)
        return client

    return fx


@pytest.fixture
def resource_client(client):
    from testutils.factories import ResourceFactory, UserFactory  # noqa: PLC0415

    user = UserFactory()
    client._resource = ResourceFactory(user=user)
    client.login(username=user.username, password=user._password)
    return client


@pytest.fixture
def resources(admin_user):
    from testutils.factories import ResourceFactory, UserFactory  # noqa: PLC0415
    from testutils.permissions import add_permissions  # noqa: PLC0415

    r_admin = ResourceFactory(user=admin_user)
    r_viewer = ResourceFactory(user=UserFactory(username='viewer'))
    r_manager = ResourceFactory(user=UserFactory(username='manager'))
    r_regular = ResourceFactory(user=UserFactory(username='regular'))
    r_other = ResourceFactory(user=UserFactory(username='other'))
    cast('Resource', r_viewer)
    cast('Resource', r_manager)
    add_permissions(r_viewer.user, 'core.view_any_timesheet')
    add_permissions(r_manager.user, 'core.manage_any_timesheet')

    return {
        'admin': r_admin,
        'viewer': r_viewer,
        'manager': r_manager,
        'regular': r_regular,
        'other': r_other,
    }


@pytest.fixture
def timesheet_api_user():
    from testutils.permissions import add_permissions
    from testutils.factories import UserFactory

    user = UserFactory()

    add_permissions(user, 'core.view_any_timesheet')
    add_permissions(user, 'core.manage_any_timesheet')

    return user


@pytest.fixture
def timesheet_api_staff_user():
    from testutils.permissions import add_permissions
    from testutils.factories import UserFactory

    user = UserFactory()

    add_permissions(user, 'core.view_any_timesheet')
    add_permissions(user, 'core.manage_any_timesheet')

    user.is_staff = True
    user.save()

    return user
