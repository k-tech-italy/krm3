import typing

import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from testutils.date_utils import _dt
from testutils.factories import ResourceFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import DayEntry, Resource, TaskEntry


@pytest.fixture
def resource():
    return ResourceFactory()


@pytest.fixture
def other_resource():
    return ResourceFactory()


@pytest.fixture
def tasks(resource, other_resource):
    from testutils.factories import TaskFactory

    return [
        contract := TaskFactory(resource=resource, contract=True),
        TaskFactory(resource=resource, contract=contract),
        TaskFactory(resource=other_resource, contract=True),
    ]


@pytest.fixture
def task_entries(resource, tasks):
    from testutils.factories import TaskEntryFactory

    return [
        TaskEntryFactory(resource=tasks[0].resource, task=tasks[0], date=_dt('2022-01-01')),
        TaskEntryFactory(resource=tasks[1].resource, task=tasks[1], date=_dt('2022-01-01')),
        TaskEntryFactory(resource=tasks[2].resource, task=tasks[2], date=_dt('2022-01-01')),
        TaskEntryFactory(resource=tasks[0].resource, task=tasks[0], date=_dt('2022-01-02')),
        TaskEntryFactory(resource=tasks[1].resource, task=tasks[1], date=_dt('2022-01-02')),
        TaskEntryFactory(resource=tasks[2].resource, task=tasks[2], date=_dt('2022-01-02')),
    ]


@pytest.mark.parametrize(
    'user, expected',
    [
        pytest.param('anon', status.HTTP_403_FORBIDDEN, id='anon'),
        pytest.param('regular', status.HTTP_200_OK, id='regular'),
    ],
)
def test_rejects_list_anonymous(
    user: str, expected, regular_user, staff_user, admin_user, resource: 'Resource', api_client
):
    url = reverse('timesheet-api:api-task-entry-list')
    if user == 'regular':
        usr = regular_user
    else:
        usr = None
    response = api_client(user=usr).get(
        url, data={'resource_id': resource.pk, 'start_date': '2022-01-01', 'end_date': '2022-01-07'}
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    'klass, user, expected',
    [
        pytest.param('day-entry', 'other', 2, id='day-other'),
        pytest.param('day-entry', 'self', 2, id='day-self'),
    ],
)
def test_can_list_time_entries(klass: str, user: str, expected: int, task_entries, resource: 'Resource', other_resource: 'Resource', api_client):
    url = reverse(f'timesheet-api:api-{klass}-list')
    if user == 'self':
        usr = resource.user
    else:
        usr = other_resource.user
    response = api_client(user=usr).get(
        url, data={'resource_id': resource.pk, 'start_date': '2022-01-01', 'end_date': '2022-01-07'}
    )
    assert response.status_code == status.HTTP_200_OK
    assert expected
