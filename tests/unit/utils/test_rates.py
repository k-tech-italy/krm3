from datetime import date
from decimal import Decimal

import responses
from testutils.factories import CurrencyFactory, ExpenseFactory

from krm3.core.models import Expense
from krm3.utils.rates import update_rates


@responses.activate
def test_update_rates_converts_all_same_day_expenses(mock_rate_provider):
    """Different currencies all convert to the base currency at the same rate."""
    day = date(2026, 1, 1)
    mock_rate_provider(day, 'EUR,GBP,USD', {'EUR': 0.2, 'GBP': 2, 'USD': 1})

    expense1 = ExpenseFactory(
        day=day, amount_currency=100, amount_base=None, amount_reimbursement=None, currency=CurrencyFactory(iso3='GBP')
    )
    expense2 = ExpenseFactory(
        day=day, amount_currency=100, amount_base=None, amount_reimbursement=None, currency=CurrencyFactory(iso3='EUR')
    )
    expense3 = ExpenseFactory(
        day=day, amount_currency=100, amount_base=None, amount_reimbursement=None, currency=CurrencyFactory(iso3='USD')
    )

    update_rates(Expense.objects.filter(id__in=[expense1.id, expense2.id, expense3.id]))

    expense1.refresh_from_db()
    expense2.refresh_from_db()
    expense3.refresh_from_db()

    assert expense1.amount_base == Decimal(10)
    assert expense2.amount_base == Decimal(100)
    assert expense3.amount_base == Decimal(20)
    assert expense1.amount_reimbursement is not None
    assert expense2.amount_reimbursement is not None
    assert expense3.amount_reimbursement is not None
