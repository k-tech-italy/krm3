import pytest
from factory.fuzzy import FuzzyChoice


@pytest.fixture()
def euro_currency():
    from krm3.currencies.models import Currency
    Currency.objects.get(iso3='EUR')


@pytest.fixture()
def mission(euro_currency):
    from factories import MissionFactory
    return MissionFactory()


@pytest.fixture()
def expense(categories, payment_types, document_types):
    from factories import ExpenseFactory
    return ExpenseFactory(
        category=FuzzyChoice(categories),
        payment_type=FuzzyChoice(payment_types),
        document_type=FuzzyChoice(document_types),
    )
