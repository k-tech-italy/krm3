import pytest
from factory.fuzzy import FuzzyChoice


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
