from decimal import Decimal as D  # noqa: N817

import pytest
from constance.test import override_config
from ktcalendars.utils import dt
from testutils.factories import CurrencyFactory, ExpenseFactory, RateFactory

@pytest.fixture
def currencies(db):
    return {
        'eur': CurrencyFactory.create(iso3='EUR'),
        'plz': CurrencyFactory.create(iso3='PLZ'),
        'usd': CurrencyFactory.create(iso3='USD'),
        'chf': CurrencyFactory.create(iso3='CHF'),
    }


@pytest.mark.parametrize(
    'curr, rates, refreshed, expectation',
    [
        pytest.param('eur', None, {'EUR', 'USD', 'GBP'}, D('111.0'), id='eur-no-rate'),
        pytest.param('usd', None, {'EUR', 'USD', 'GBP'}, D('99.90'), id='usd-no-rate'),
        pytest.param('plz', None, {'EUR', 'USD', 'GBP', 'PLZ'}, D('24.98'), id='plz-no-rate'),
        pytest.param('plz', {'EUR': 1, 'PLZ': 2.1}, {'USD', 'GBP'}, D('52.86'), id='plz-rate'),
    ],
)
def test_update_rates(curr, rates, refreshed, expectation, currencies, oxr) -> None:
    from krm3.core.models import Expense
    from krm3.utils.rates import update_rates

    if rates:
        RateFactory(day=dt('2020-02-01'), rates=rates)

    oxr.known_rates['2020-02-01'] = {'EUR': 0.9, 'PLZ': 4.0, 'GBP': 0.8}

    ExpenseFactory.create(day=dt('2020-02-01'), amount_currency=111, currency=currencies[curr])

    qs = Expense.objects.all()

    with override_config(CURRENCIES='EUR,GBP,USD'):
        update_rates(None, qs)

    # once per day
    assert [c.args[0] for c in oxr.get_historical.call_args_list] == (['2020-02-01'] if curr != 'eur' else [])
    # every currency needed that day was requested in that single call
    if oxr.get_historical.call_count > 0:
        assert set(oxr.get_historical.call_args.kwargs['symbols']) == refreshed
    expense = Expense.objects.first()
    assert expense.amount_base == expectation
    assert expense.amount_reimbursement == -1 * expectation
