import datetime
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ProjectFactory, TaskFactory

from krm3.core.forms import ContractForm
from krm3.core.models import Contract
from krm3.utils.dates import KrmDay

@pytest.fixture
def contracts_and_tasks():
    project = ProjectFactory(start_date=datetime.date(2019, 1, 1), end_date=None)

    c1: 'Contract' = ContractFactory(period=(_dt('2020-01-01'), _dt('2020-07-01')))
    c2: 'Contract' = ContractFactory(resource=c1.resource, period=(_dt('2020-07-01'), _dt('2021-01-01')))
    c3: 'Contract' = ContractFactory(resource=c1.resource, period=(_dt('2021-01-01'), None))
    c4: 'Contract' = ContractFactory(period=(_dt('2019-01-01'), _dt('2020-05-01')))
    c5: 'Contract' = ContractFactory(resource=c4.resource, period=(_dt('2020-05-01'), _dt('2020-10-01')))

    return {
        'contracts': [c1, c2, c3, c4, c5],
        'tasks': [
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 4, 1),
                end_date=datetime.date(2020, 6, 15),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 6, 1),
                end_date=datetime.date(2020, 8, 31),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 8, 1),
                end_date=None,
            ),
            TaskFactory(
                resource=c4.resource,
                project=project,
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 3, 15),
            ),
        ],
    }


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


def test_contract_ordering():
    c1 = ContractFactory(period=(_dt('20250601'), _dt('20250630')))
    c2 = ContractFactory(period=(_dt('20250503'), _dt('20250601')))
    assert list(Contract.objects.values_list('id', flat=True)) == [c2.id, c1.id]


@pytest.mark.parametrize(
    'cnum, new_lower, new_upper, valid',
    [
        pytest.param(0, _dt('20200401'), None, True, id='c1-start-ok'),
        pytest.param(0, _dt('20200402'), None, False, id='c1-start-short'),
        pytest.param(3, None, _dt('20200316'), True, id='c4-end-ok'),
        pytest.param(3, None, _dt('20200315'), False, id='c4-end-short'),
        pytest.param(1, _dt('20200702'), None, False, id='c2-start-short'),
        pytest.param(2, None, _dt('22000101'), False, id='c3-end-short'),
    ],
)
def test_amend_contract_with_tasks(cnum, new_lower, new_upper, valid, contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][cnum]

    lower = contract.period.lower.strftime('%Y-%m-%d')
    upper = contract.period.upper.strftime('%Y-%m-%d') if contract.period.upper else ''

    if new_lower:
        lower = new_lower
    elif new_upper:
        upper = new_upper

    data = {'resource': contract.resource, 'period_0': lower, 'period_1': upper}
    form = ContractForm(instance=contract, data=data)

    assert form.is_valid() is valid, form.errors


@pytest.mark.parametrize(
    'cnum, expected',
    [
        pytest.param(0, [0, 1], id='c1'),
        pytest.param(1, [1, 2], id='c2'),
        pytest.param(2, [2], id='c3'),
        pytest.param(3, [3], id='c4'),
        pytest.param(4, [], id='c5'),
    ],
)
def test_get_tasks(cnum, expected, contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][cnum]
    assert contract.get_tasks() == [contracts_and_tasks['tasks'][x] for x in expected]
