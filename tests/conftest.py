import sys
from pathlib import Path

import pytest
from factory.fuzzy import FuzzyChoice


def pytest_configure(config):
    here = Path(__file__).parent
    # root = here.parent.parent
    sys.path.insert(0, str(here / '_extras'))


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
def client(db):
    from factories import ClientFactory
    return ClientFactory()


@pytest.fixture()
def mission(db):
    from factories import MissionFactory
    return MissionFactory()


@pytest.fixture()
def expense(categories, payment_types):
    from factories import ExpenseFactory
    return ExpenseFactory(
        category=FuzzyChoice(categories),
        payment_type=FuzzyChoice(payment_types),
    )

# @pytest.fixture()
# def mission(db):
#     return MissionFactory()
