import sys
from pathlib import Path

import pytest
import responses
from django.utils.http import urlencode


def pytest_configure(config):
    here = Path(__file__).parent
    # root = here.parent.parent
    sys.path.insert(0, str(here / '_extras'))


@pytest.fixture(autouse=True)
def dummy_currencies(settings):
    settings.CURRENCIES = ['GBP', 'EUR', 'USD']
    settings.OPEN_EXCHANGE_RATES_APP_ID = 'abc'
    settings.BASE_CURRENCY = 'EUR'


@pytest.fixture()
def mock_rate_provider(settings, db):
    def fx(day, requested, retrieved):
        responses.add(
            responses.GET,
            f'https://openexchangerates.org/api/historical/{day:%Y-%m-%d}.json?' +
            urlencode({'app_id': settings.OPEN_EXCHANGE_RATES_APP_ID, 'symbols': requested}),
            json={
                'disclaimer': 'Usage subject to terms: https://openexchangerates.org/terms',
                'license': 'https://openexchangerates.org/license',
                'timestamp': 1582588799,
                'base': 'USD',
                'rates': retrieved
            },
            status=200
        )
    return fx


@pytest.fixture()
def regular_user(db):
    from factories import UserFactory
    return UserFactory()


@pytest.fixture()
def payment_types(db):
    results = []
    from krm3.missions.models import PaymentCategory
    azienda = PaymentCategory.objects.create(title='Azienda')
    results.append(PaymentCategory.objects.create(title='Anticipo', parent=azienda))
    results.append(PaymentCategory.objects.create(title='CCA', parent=azienda))
    personale = PaymentCategory.objects.create(title='Personale')
    results.append(PaymentCategory.objects.create(title='CCP', parent=personale))
    results.append(PaymentCategory.objects.create(title='Cash', parent=personale))
    return results


@pytest.fixture()
def document_types(db):
    results = []
    from krm3.missions.models import DocumentType
    results.append(DocumentType.objects.get_or_create(title='Scontrino', default=True)[0])
    results.append(DocumentType.objects.get_or_create(title='Fattura')[0])
    results.append(DocumentType.objects.get_or_create(title='Altro')[0])
    results.append(DocumentType.objects.get_or_create(title='Disabled', active=False)[0])
    return results


@pytest.fixture()
def categories(db):
    results = []
    from krm3.missions.models import ExpenseCategory
    viaggi = ExpenseCategory.objects.create(title='Viaggi')
    results.append(ExpenseCategory.objects.create(title='Taxi', parent=viaggi))
    results.append(ExpenseCategory.objects.create(title='Train', parent=viaggi))
    vitto = ExpenseCategory.objects.create(title='Vitto')
    results.append(ExpenseCategory.objects.create(title='Pranzo', parent=vitto))
    results.append(ExpenseCategory.objects.create(title='Cena', parent=vitto))
    return results


@pytest.fixture()
def country(db):
    from factories import CountryFactory
    return CountryFactory()


@pytest.fixture()
def city(db):
    from factories import CityFactory
    return CityFactory()


@pytest.fixture()
def resource(db):
    from factories import ResourceFactory
    return ResourceFactory()


@pytest.fixture()
def project(db):
    from factories import ProjectFactory
    return ProjectFactory()


@pytest.fixture()
def krm3client(db):
    from factories import ClientFactory
    return ClientFactory()
