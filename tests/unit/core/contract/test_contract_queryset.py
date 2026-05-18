from __future__ import annotations

import typing

import pytest
from ktcalendars import KTDay
from ktcalendars.utils import dt
from testutils.factories import ContractFactory

if typing.TYPE_CHECKING:
    import datetime

    from krm3.core.models import Contract, Resource

wrong_range = pytest.raises(ValueError, match='day_range must be a tuple of length 1 or 2')
cover_missing = pytest.raises(ValueError, match='Contract cover missing for requested range')
no_cover = pytest.raises(ValueError, match='No contract found in range')


@pytest.fixture
def contracts():
    c1 = ContractFactory(period=(dt('2020-01-15'), dt('2020-02-10')))
    c2 = ContractFactory(period=(dt('2020-02-10'), dt('2020-02-20')), resource=c1.resource)
    c3 = ContractFactory(period=(dt('2020-02-21'), dt('2020-03-01')), resource=c1.resource)
    c4 = ContractFactory(period=(dt('2020-03-01'), None), resource=c1.resource)
    return [c1, c2, c3, c4, ContractFactory(period=(dt('2020-02-01'), dt('2020-03-01')))]


@pytest.mark.parametrize(
    'day, expected',
    [
        pytest.param(dt('2020-02-19'), 1, id='single-ok'),
        pytest.param(KTDay('2020-02-20'), None, id='single-none'),
    ],
)
def test_contract_queryset_by_day(day: datetime.date, expected: int, contracts):
    from krm3.core.models import Contract

    result = Contract.objects.by_day(contracts[0].resource, day)
    if expected is None:
        assert result is None
    else:
        assert result == contracts[expected]


@pytest.mark.parametrize(
    'contract, rng, partial, atomic, expected',
    [
        pytest.param(0, [dt('2020-02-01'), None], None, False, False, id='gap-NOK-2020-02-20-partial-none'),
        pytest.param(0, [dt('2020-02-01'), None], False, False, False, id='gap-NOK-2020-02-20-partial-false'),
        pytest.param(0, [dt('2020-02-01'), None], True, False, True, id='gap-OK-2020-02-20-partial-true'),
        pytest.param(0, [dt('2020-03-01'), None], False, False, True, id='all-covered'),
        pytest.param(0, [dt('2020-02-20'), None], False, False, False, id='missing-lower'),
        pytest.param(0, [dt('2020-02-29'), None], True, False, True, id='ok'),
        pytest.param(4, [dt('2020-01-01'), dt('2020-01-31')], True, False, False, id='contract-before'),
        pytest.param(4, [dt('2020-01-01'), dt('2020-02-01')], True, False, True, id='contract-lower-partial'),
        pytest.param(4, [dt('2020-01-01'), dt('2020-02-01')], False, False, False, id='contract-lower-non-partial'),
        pytest.param(0, [dt('2020-02-08'), dt('2020-02-12')], True, True, False, id='atomic-true'),
        pytest.param(0, [dt('2020-02-08'), dt('2020-02-12')], True, False, True, id='atomic-false'),
        pytest.param(0, [dt('2020-02-08'), dt('2020-02-12')], True, None, True, id='atomic-none'),
    ],
)
def test_contract_queryset_range_cover_missing(
    contract: int, rng, partial: bool | None, atomic: bool | None, expected: bool, contracts: list[Contract]
):
    res: Resource = contracts[contract].resource
    params = {}
    if partial is not None:
        params['partial'] = partial
    if atomic is not None:
        params['atomic'] = atomic
    assert res.has_contract_cover(*rng, **params) is expected
