import pytest
from factory.fuzzy import FuzzyChoice


@pytest.fixture()
def euro_currency(db):
    from factories import CurrencyFactory
    return CurrencyFactory(iso3='EUR', title='Euro', symbol='€')


@pytest.fixture()
def mission(euro_currency):
    from factories import MissionFactory
    return MissionFactory()


@pytest.fixture()
def expense(categories, payment_types):
    from factories import ExpenseFactory
    return ExpenseFactory(
        category=FuzzyChoice(categories),
        payment_type=FuzzyChoice(payment_types),
    )
