import datetime
import typing

import pytest

from krm3.projects.forms import TaskForm
from testutils.factories import ContractFactory, ProjectFactory, ResourceFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract, Resource

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
    c1: 'Contract' = ContractFactory(period=(datetime.date(2020, 1, 1), datetime.date(2025, 1, 1)))
    ContractFactory(resource=c1.resource, period=(datetime.date(2025, 1, 1), None))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': c1.resource,
            'start_date': datetime.date(2024, 12, 1),
            'end_date': datetime.date(2025, 2, 1),
        }
    )
    assert form.is_valid() is True


def test_non_contiguous_contracts(project_2020_open):
    c1: 'Contract' = ContractFactory(period=(datetime.date(2020, 1, 1), datetime.date(2025, 1, 1)))
    ContractFactory(resource=c1.resource, period=(datetime.date(2025, 1, 2), None))

    form = TaskForm(
        data=base
        | {
            'project': project_2020_open,
            'resource': c1.resource,
            'start_date': datetime.date(2024, 12, 1),
            'end_date': datetime.date(2025, 1, 1),
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
