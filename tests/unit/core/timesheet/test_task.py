import datetime
import typing

import pytest
from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ProjectFactory, ResourceFactory, TaskFactory

from krm3.core.models import Contract
from krm3.projects.forms import TaskForm
from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Task

base = {
    'title': 'task1',
    'color': '#333333',
    'work_price': 0,
    'on_call_price': 0,
    'travel_price': 0,
    'overtime_price': 0,
}


@pytest.fixture
def project_2020_open():
    return ProjectFactory()


@pytest.mark.parametrize(
    'end_date',
    [
        pytest.param(None, id='open-ended'),
        pytest.param(_dt('2031-01-01'), id='closed-ended'),
    ],
)
def test_task_with_contract(end_date, project_2020_open):
    contract: 'Contract' = ContractFactory(period=(_dt('2020-01-01'), end_date))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': contract.resource,
            'period_0': contract.period.lower.strftime('%Y-%m-%d'),
            'period_1': end_date.strftime('%Y-%m-%d') if end_date else None,
        }
    )
    assert form.is_valid() is True, form.errors


def test_task_spanning_contracts(project_2020_open):
    c1: 'Contract' = ContractFactory(period=(_dt('20200101'), _dt('20220101')))
    ContractFactory(resource=c1.resource, period=(_dt('20220101'), _dt('20250101')))
    ContractFactory(resource=c1.resource, period=(_dt('20250101'), None))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': c1.resource,
            'period_0': '2021-12-01',
            'period_1': '2025-03-01',
        }
    )
    assert form.is_valid() is True, form.errors


@pytest.mark.parametrize(
    'contracts',
    [
        pytest.param(
            [
                [_dt('2020-01-01'), _dt('2025-01-01')],
                [_dt('2025-01-02'), None],
            ],
            id='gap-end',
        ),
        pytest.param(
            [
                [_dt('2025-01-02'), None],
            ],
            id='gap-start',
        ),
        pytest.param(
            [
                [_dt('2020-01-01'), _dt('2024-01-01')],
                [_dt('2024-04-01'), _dt('2026-01-01')],
            ],
            id='gap-middle',
        ),
    ],
)
def test_non_contiguous_contracts(contracts, project_2020_open):
    c1: 'Contract' = ContractFactory(period=(contracts[0][0], contracts[0][1]))
    for contract in contracts[1:]:
        ContractFactory(resource=c1.resource, period=(contract[0], contract[1]))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': c1.resource,
            'period_0': '2022-12-01',
            'period_1': '2025-01-02',
        }
    )
    assert form.is_valid() is False
    assert form.errors == {'period': ['Contract matching task period not found']}


def test_task_without_contract(project_2020_open):
    resource: 'Resource' = ResourceFactory()
    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': resource,
            'period_0': '2020-05-01',
            'period_1': '2020-05-10',
        }
    )
    assert form.is_valid() is False
    assert form.errors == {'period': ['Contract matching task period not found']}


@pytest.mark.parametrize(
    'start_date, end_date',
    [
        pytest.param(_dt('2020-01-02'), None),
        pytest.param(_dt('2020-01-02'), _dt('2020-01-04')),
        pytest.param(_dt('2020-01-01'), _dt('2020-01-03')),
    ],
)
def test_task_outside_contract(start_date, end_date, project_2020_open):
    contract: 'Contract' = ContractFactory(period=(start_date, end_date))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': contract.resource,
            'period_0': '2020-01-01',
            'period_1': '2020-01-04',
        }
    )

    assert form.is_valid() is False
    assert form.errors == {'period': ['Contract matching task period not found']}


@pytest.fixture
def orphan_scenario():
    c1: Contract = ContractFactory.create()
    c2: Contract = ContractFactory.create()

    task: 'Task' = TaskFactory.create(contract=c1)
    task2: 'Task' = TaskFactory.create(contract=c2)

    te_date = task.period.lower + relativedelta(days=1)

    c1.build_day(te_date, holiday_hours=4, task_entries=[{'task': task, 'day_shift_hours': 1}])
    c2.build_day(te_date, task_entries=[{'task': task2, 'day_shift_hours': 1}])

    return task, task2


def test_orphan_te_check(orphan_scenario):
    task, task2 = orphan_scenario

    data = model_to_dict(task)
    period = data.pop('period')
    data['period_0'], data['period_1'] = period.lower, period.upper

    form = TaskForm(instance=task, data=data | {'color': '#FFFFFF'})
    assert form.is_valid() is True, form.errors

    form = TaskForm(instance=task, data=data | {'color': '#FFFFFF', 'period_0': str(KrmDay(period.lower) + 2)})
    assert form.is_valid() is False, form.errors
    assert form.errors == {'__all__': ['Would leave 1 orphan task_entries']}
