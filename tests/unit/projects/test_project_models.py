import datetime
import typing
from contextlib import nullcontext as does_not_raise

import freezegun
import pytest
from django.core import exceptions
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, POFactory, ProjectFactory, TaskFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract

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
    [TaskFactory, ProjectFactory, POFactory, ],
)
def test_project_and_po_period(period, expectation, factory):
    d = {}
    if factory == TaskFactory:
        from krm3.core.models import Task, Contract, Resource
        d['contract'] = True
    with expectation:
        obj = factory(period=period, **d)
        assert bool(obj.id)


def test_raises_when_starting_before_related_project():
    project = ProjectFactory(period=(_dt('2024-01-01'), None))

    contract = ContractFactory()

    with does_not_raise():
        _valid_task_starting_on_same_day = TaskFactory(project=project, period=(project.period.lower, None), contract=contract)
        _valid_task_starting_later = TaskFactory(project=project, period=(_dt('2025-12-31'), None), contract=contract)

    # NOTE: this will keep the instance around for later checks
    with pytest.raises(exceptions.ValidationError) as excinfo:
        _invalid_task_starting_earlier = TaskFactory(
            title='Invalid', project=project, period=(_dt('2020-01-01'), None)
        )
    assert ['Missing contract cover for the range [2020-01-01:...)'] == excinfo.value.messages
