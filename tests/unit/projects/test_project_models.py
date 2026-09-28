from contextlib import nullcontext as does_not_raise

import freezegun
import pytest
from django.core import exceptions
from psycopg.types.range import DateRange
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, POFactory, ProjectFactory, TaskFactory

required = pytest.raises(exceptions.ValidationError, match='is required')
order = pytest.raises(exceptions.ValidationError, match='End date must be at least one day after start date')
ok = does_not_raise()


@freezegun.freeze_time(_dt('2024-01-01'))
@pytest.mark.parametrize(
    'period, expectation',
    (
        pytest.param((_dt('2024-01-01'), None), ok, id='dt-none'),
        pytest.param((_dt('2024-01-01'), _dt('2024-01-02')), ok, id='dt-dt'),
        pytest.param((None, None), required, id='none-none'),
        pytest.param((None, _dt('2030-01-02')), required, id='none-dt'),
        pytest.param((_dt('2024-01-01'), _dt('2024-01-01')), order, id='dates-order'),
    ),
)
@pytest.mark.parametrize(
    'factory',
    [
        TaskFactory,
        ProjectFactory,
        POFactory,
    ],
)
def test_project_and_po_period(period, expectation, factory):
    d = {}
    if factory == TaskFactory:
        d['contract'] = True
    with expectation:
        obj = factory(period=period, **d)
        assert bool(obj.id)


def test_raises_when_starting_before_related_project():
    project = ProjectFactory(period=(_dt('2010-01-01'), None))

    contract = ContractFactory()

    with does_not_raise():
        _valid_task_starting_on_same_day = TaskFactory(
            project=project, period=(_dt('2020-01-01'), None), resource=contract.resource
        )
        _valid_task_starting_later = TaskFactory(
            project=project, period=(_dt('2025-12-31'), None), resource=contract.resource
        )

    # NOTE: this will keep the instance around for later checks
    with pytest.raises(exceptions.ValidationError) as excinfo:
        _invalid_task_starting_earlier = TaskFactory(
            title='Invalid', project=project, period=(_dt('2019-12-31'), None), resource=contract.resource
        )
    assert excinfo.value.messages == ['Missing contract cover for the range [2019-12-31:...)']


def test_accepts_task_period_contained_within_project():
    project = ProjectFactory(period=(_dt('2021-01-01'), _dt('2026-01-01')))
    contract = ContractFactory(period=(_dt('2020-01-01'), None))

    task = TaskFactory(
        project=project,
        resource=contract.resource,
        period=(_dt('2022-01-01'), _dt('2025-01-01')),
    )

    assert task.pk


@pytest.mark.parametrize(
    'task_period',
    (
        pytest.param((_dt('2020-01-01'), _dt('2025-01-01')), id='starts-before-project'),
        pytest.param((_dt('2022-01-01'), _dt('2027-01-01')), id='ends-after-project'),
        pytest.param((_dt('2022-01-01'), None), id='open-task-in-bounded-project'),
    ),
)
def test_rejects_task_period_outside_project(task_period):
    project = ProjectFactory(period=(_dt('2021-01-01'), _dt('2026-01-01')))
    contract = ContractFactory(period=(_dt('2020-01-01'), None))

    with pytest.raises(exceptions.ValidationError, match='Task period must be contained within the project period'):
        TaskFactory(project=project, resource=contract.resource, period=task_period)


def test_allows_project_period_change_when_tasks_remain_inside():
    project = ProjectFactory(period=(_dt('2020-01-01'), _dt('2030-01-01')))
    contract = ContractFactory(period=(_dt('2020-01-01'), None))
    TaskFactory(
        project=project,
        resource=contract.resource,
        period=(_dt('2022-01-01'), _dt('2028-01-01')),
    )

    project.period = DateRange(_dt('2021-01-01'), _dt('2029-01-01'))
    project.save()


def test_rejects_project_period_change_that_excludes_task():
    project = ProjectFactory(period=(_dt('2020-01-01'), _dt('2030-01-01')))
    contract = ContractFactory(period=(_dt('2020-01-01'), None))
    TaskFactory(
        project=project,
        resource=contract.resource,
        period=(_dt('2022-01-01'), _dt('2028-01-01')),
    )

    project.period = DateRange(_dt('2023-01-01'), _dt('2029-01-01'))

    with pytest.raises(exceptions.ValidationError, match='The project period would exclude existing tasks'):
        project.save()
