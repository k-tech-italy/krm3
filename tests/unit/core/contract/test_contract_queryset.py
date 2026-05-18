from __future__ import annotations

from contextlib import nullcontext as does_not_raise

import datetime
import typing

import pytest

from krm3.utils.dates import KrmDay
from testutils.date_utils import _dt
from testutils.factories import ContractFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract

wrong_range = pytest.raises(ValueError, match='day_range must be a tuple of length 1 or 2')
cover_missing = pytest.raises(ValueError, match='Contract cover missing for requested range')
no_cover = pytest.raises(ValueError, match='No contract found in range')


@pytest.fixture
def contracts():
    c1 = ContractFactory(period=(_dt('2020-01-15'), _dt('2020-02-10')))
    c2 = ContractFactory(period=(_dt('2020-02-10'), _dt('2020-02-20')), resource=c1.resource)
    c3 = ContractFactory(period=(_dt('2020-02-21'), _dt('2020-03-01')), resource=c1.resource)
    c4 = ContractFactory(period=(_dt('2020-03-01'), None), resource=c1.resource)
    return [c1, c2, c3, c4, ContractFactory(period=(_dt('2020-02-01'), _dt('2020-03-01')))]


@pytest.mark.parametrize(
    'days, expected',
    [
        pytest.param([_dt('2020-02-09'), _dt('2020-02-10')], {0}, id='single-ok'),
        pytest.param([_dt('2020-02-09'), _dt('2020-02-11')], {1, 0}, id='double-ok'),
        pytest.param([_dt('2020-02-21'), None], {3, 2}, id='none-ok'),
        pytest.param([_dt('2020-02-21'), datetime.date.max], {3, 2}, id='max-ok'),
        pytest.param([_dt('2010-01-20'), _dt('2019-01-21')], no_cover, id='no-contract'),
        pytest.param(
            [_dt('2020-02-21'), _dt('2020-03-10')],
            {3, 2},
            id='multi-inf-ok',
        ),
        pytest.param(
            [_dt('2020-02-07'), _dt('2020-02-20')],
            {0, 1},
            id='multi-2',
        ),
        pytest.param(
            [_dt('2020-01-07'), _dt('2020-02-07')],
            cover_missing,
            id='multi-2-nok',
        ),
    ],
)
def test_contract_queryset_by_day_range(contracts: list[Contract], days: list[datetime.date], expected: set[int]):
    from krm3.core.models import Contract

    if isinstance(expected, set):
        result = set(Contract.objects.by_day_range(contracts[0].resource, *days))
        assert result == {contracts[x] for x in expected}
    else:
        with expected:
            Contract.objects.by_day_range(contracts[0].resource, *days)


@pytest.mark.parametrize(
    'resource, range, expectation',
    [
        pytest.param(0, [_dt('2020-02-01'), None], cover_missing, id='missing20'),
        pytest.param(
            3,
            [_dt('2020-03-01'), _dt('2020-03-31')],
            does_not_raise(),
            id='covered',
        ),
        pytest.param(
            3,
            [_dt('2020-02-10'), _dt('2020-03-01')],
            cover_missing,
            id='upper-bound',
        ),
        pytest.param(
            3,
            [_dt('2020-02-20'), _dt('2020-02-29')],
            cover_missing,
            id='lower-bound',
        ),
        pytest.param(
            4,
            [_dt('2020-01-10'), _dt('2020-01-31')],
            no_cover,
            id='past',
        ),
        pytest.param(
            4,
            [_dt('2020-03-01'), _dt('2020-03-10')],
            no_cover,
            id='future',
        ),
    ],
)
def test_contract_queryset_range_cover_missing(resource, range, expectation, contracts: list[Contract]):
    from krm3.core.models import Contract

    with expectation:
        Contract.objects.by_day_range(contracts[resource].resource, *range)


@pytest.mark.parametrize(
    'day, expected',
    [
        pytest.param(_dt('2020-02-19'), 1, id='single-ok'),
        pytest.param(KrmDay('2020-02-20'), None, id='single-none'),
    ],
)
def test_contract_queryset_by_day(day: datetime.date, expected: int, contracts):
    from krm3.core.models import Contract

    result = Contract.objects.by_day(contracts[0].resource, day)
    if expected is None:
        assert result is None
    else:
        assert result == contracts[expected]
