import datetime
import typing

import pytest
from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict

from krm3.projects.forms import TaskForm
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ProjectFactory, ResourceFactory, TaskFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract, Resource, Task

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
    return ProjectFactory(start_date=datetime.date(2020, 1, 1), end_date=None)


@pytest.mark.parametrize(
    'end_date',
    [
        pytest.param(None, id='open-ended'),
        pytest.param(datetime.date(2031, 1, 1), id='closed-ended'),
    ],
)
def test_task_with_contract(end_date, project_2020_open):
    contract: 'Contract' = ContractFactory(period=(datetime.date(2020, 1, 1), end_date))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': contract.resource,
            'start_date': contract.period.lower,
            'end_date': datetime.date(2030, 12, 31),
        }
    )
    assert form.is_valid() is True


def test_task_spanning_contracts(project_2020_open):
    c1: 'Contract' = ContractFactory(period=(_dt('20200101'), _dt('20220101')))
    ContractFactory(resource=c1.resource, period=(_dt('20220101'), _dt('20250101')))
    ContractFactory(resource=c1.resource, period=(_dt('20250101'), None))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': c1.resource,
            'start_date': _dt('20211201'),
            'end_date': _dt('20250301'),
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
            'start_date': _dt('2022-12-01'),
            'end_date': _dt('2025-01-01'),
        }
    )
    assert form.is_valid() is False
    assert form.errors == {'__all__': ['Contract matching task period not found']}


def test_task_without_contract(project_2020_open):
    resource: 'Resource' = ResourceFactory()
    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': resource,
            'start_date': datetime.date(2020, 5, 1),
            'end_date': datetime.date(2020, 5, 10),
        }
    )
    assert form.is_valid() is False
    assert form.errors == {'__all__': ['Contract matching task period not found']}


@pytest.mark.parametrize(
    'start_date, end_date',
    [
        pytest.param(datetime.date(2020, 1, 2), None),
        pytest.param(datetime.date(2020, 1, 2), datetime.date(2020, 1, 4)),
        pytest.param(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3)),
    ],
)
def test_task_outside_contract(start_date, end_date, project_2020_open):
    contract: 'Contract' = ContractFactory(period=(start_date, end_date))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': contract.resource,
            'start_date': datetime.date(2020, 1, 1),
            'end_date': datetime.date(2020, 1, 4),
        }
    )

    assert form.is_valid() is False
    assert form.errors == {'__all__': ['Contract matching task period not found']}


@pytest.fixture
def orphan_scenario():
    from krm3.core.models import TimeEntry  # noqa: PLC0415

    task: 'Task' = TaskFactory.create()
    task2: 'Task' = TaskFactory.create()

    ContractFactory(resource=task.resource, period=(task.start_date, task.end_date))
    ContractFactory(resource=task2.resource, period=(task2.start_date, task2.end_date))

    te_date = task.start_date + relativedelta(days=2)

    TimeEntry.objects.create(resource=task.resource, date=te_date, day_shift_hours=0, holiday_hours=4)
    TimeEntry.objects.create(resource=task.resource, date=te_date, task=task, day_shift_hours=1)
    TimeEntry.objects.create(resource=task2.resource, date=te_date, task=task2, day_shift_hours=1)
    return task, task2


def test_orphan_te_check_ok(orphan_scenario):
    task, task2 = orphan_scenario

    form = TaskForm(instance=task, data=model_to_dict(task) | {'color': '#FFFFFF'})
    assert form.is_valid() is True, form.errors


def test_orphan_te_check_nok(orphan_scenario):
    task, task2 = orphan_scenario

    form = TaskForm(instance=task, data=model_to_dict(task) | {'color': '#FFFFFF', 'end_date': task.start_date})
    assert form.is_valid() is False, form.errors
    assert form.errors == {'__all__': ['Would leave 1 orphan time_entries']}
