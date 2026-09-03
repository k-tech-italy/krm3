import pytest
from factory.fuzzy import FuzzyChoice
from testutils.factories import ExpenseFactory, MissionFactory

from krm3.currencies.models import Currency


@pytest.fixture
def euro_currency():
    Currency.objects.get(iso3='EUR')


@pytest.fixture
def mission(euro_currency):
    return MissionFactory()


@pytest.fixture
def expense(categories, payment_types, document_types):
    return ExpenseFactory(
        category=FuzzyChoice(categories.expenses.values()),
        payment_type=FuzzyChoice(categories.payments.values()),
        document_type=FuzzyChoice(document_types),
    )
