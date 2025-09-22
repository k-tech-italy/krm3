import datetime
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from testutils.date_utils import _dt
from testutils.factories import ContractFactory

from krm3.utils.dates import KrmDay

def test_contract_upper_bond_must_be_one_day_greater():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 1)
    with pytest.raises(ValidationError, match='End date must be at least one day after start date.'):
        ContractFactory(period=(start_dt, end_dt))


def test_create_contract_with_correct_period():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 2)
    ContractFactory(period=(start_dt, end_dt))


@pytest.mark.parametrize(
    'period, day, expected',
    [
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-02'), True),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-31'), True),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-01'), False),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-02-01'), False),
        ((_dt('2020-01-02'), None), _dt('2020-01-02'), True),
        ((_dt('2020-01-02'), None), _dt('2020-01-01'), False),
    ],
)
def test_falls_in(period: tuple, day: datetime.date | KrmDay, expected: bool):
    contract = ContractFactory(period=period)
    assert contract.falls_in(day) is expected
