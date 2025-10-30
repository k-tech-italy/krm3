import typing

import pytest
from rest_framework.reverse import reverse

from krm3.core.models import TimeEntry
from testutils.date_utils import _dt
from testutils.factories import TaskFactory, TimeEntryFactory

if typing.TYPE_CHECKING:
    from krm3.core.models.projects import Task


@pytest.fixture
def scenario_time_entries(resources):
    t1 = TaskFactory(resource=resources['admin'])
    t2 = TaskFactory(resource=resources['regular'])  # other resource
    return {
        'resources': resources,
        'tasks': {
            't1': t1,
            't2': t2,
        },
        'time_entries': {
            1: TimeEntryFactory(resource=resources['admin'], date=_dt('20250824'), task=t1, day_shift_hours=2),
            2: TimeEntryFactory(resource=resources['admin'], date=_dt('20250825'), task=t1, day_shift_hours=2),
            3: TimeEntryFactory(resource=resources['admin'], date=_dt('20250826'), task=t1, day_shift_hours=2),
            4: TimeEntryFactory(resource=resources['admin'], date=_dt('20250827'), task=t1, day_shift_hours=2),
            5: TimeEntryFactory(resource=resources['admin'], date=_dt('20250828'), task=t1, day_shift_hours=2),
            6: TimeEntryFactory(resource=resources['admin'], date=_dt('20250829'), task=t1, day_shift_hours=2),
            7: TimeEntryFactory(resource=resources['regular'], date=_dt('20250827'), task=t2, day_shift_hours=2),
        },
    }


@pytest.mark.parametrize(
    'usr, num',
    [
        pytest.param('admin', 7, id='admin'),
        pytest.param('viewer', 7, id='viewer'),
        pytest.param('manager', 7, id='manager'),
        pytest.param('regular', 1, id='regular'),
    ],
)
def test_time_entry_can_list(usr: str, num: int, scenario_time_entries, api_client):
    requestor = scenario_time_entries['resources'][usr].user
    url = reverse('timesheet-api:api-time-entry-list')
    response = api_client(user=requestor).get(url)
    assert response.status_code == 200, response.data.get('detail')
    assert response.data['count'] == num


@pytest.mark.parametrize(
    'usr, expected, num',
    [
        pytest.param('admin', 200, 1, id='admin'),
        pytest.param('viewer', 200, 1, id='viewer'),
        pytest.param('manager', 200, 1, id='manager'),
        pytest.param('regular', 404, 0, id='regular'),
    ],
)
def test_time_entry_can_get(usr: str, expected: int, num: int, scenario_time_entries, api_client):
    requestor = scenario_time_entries['resources'][usr].user
    url = reverse('timesheet-api:api-time-entry-detail', kwargs={'pk': scenario_time_entries['time_entries'][1].id})
    response = api_client(user=requestor).get(url)
    assert response.status_code == expected, response.data.get('detail')


# TODO : should refactor according to #424
@pytest.mark.parametrize(
    'usr, expected, num',
    [
        pytest.param('admin', 201, 1, id='admin'),
        pytest.param('viewer', 403, 1, id='viewer'),
        pytest.param('manager', 201, 1, id='manager'),
        pytest.param('regular', 403, 0, id='regular'),
    ],
)
def test_time_entry_can_create(usr: str, expected: int, num: int, scenario_time_entries, api_client):
    requestor = scenario_time_entries['resources'][usr].user
    url = reverse('timesheet-api:api-time-entry-list')
    task = scenario_time_entries['tasks']['t1']
    resource = scenario_time_entries['tasks']['t1'].resource
    response = api_client(user=requestor).post(
        url,
        data={
            'dates': [_dt('20250824')],  # TODO: This is de facto an upsert. Should it be?
            'task_id': task.id,
            'day_shift_hours': 2,
            'resource_id': resource.id,
        },
        content_type='application/json',
    )
    assert response.status_code == expected, response.data.get('detail')


# TODO: see #424, as of now FE does not use this API
@pytest.mark.parametrize(
    'usr, expected',
    [
        pytest.param('admin', 200, id='admin'),
        pytest.param('viewer', 403, id='viewer'),
        pytest.param('manager', 200, id='manager'),
        pytest.param('regular', 404, id='regular'),
    ],
)
def test_time_entry_can_update(usr: str, expected: int, scenario_time_entries, api_client):
    url = reverse('timesheet-api:api-time-entry-detail', kwargs={'pk': scenario_time_entries['time_entries'][1].id})
    requestor = scenario_time_entries['resources'][usr].user
    task = scenario_time_entries['tasks']['t1']

    response = api_client(user=requestor).put(
        url,
        data={'date': _dt('20250824'), 'task': task.id, 'day_shift_hours': 4, 'resource': task.resource.id},
        content_type='application/json',
    )
    assert response.status_code == expected, response.data.get('detail')
    if response.status_code == 200:
        assert response.data['day_shift_hours'] == '4.00'


@pytest.mark.parametrize(
    'usr, expected',
    [
        pytest.param('admin', 204, id='admin'),
        pytest.param('viewer', 403, id='viewer'),
        pytest.param('manager', 204, id='manager'),
        pytest.param('regular', 404, id='regular'),
    ],
)
def test_time_entry_can_delete(usr: str, expected: int, scenario_time_entries, api_client):
    pk = scenario_time_entries['time_entries'][1].id
    url = reverse('timesheet-api:api-time-entry-detail', kwargs={'pk': pk})
    requestor = scenario_time_entries['resources'][usr].user

    response = api_client(user=requestor).delete(url)
    assert response.status_code == expected, response.data.get('detail')

    assert TimeEntry.objects.filter(pk=pk).count() == 0 if expected == 204 else 1


@pytest.mark.parametrize(
    'closed, updated_status, deleted_status',
    [
        pytest.param(False, 200, 204, id='open'),
        pytest.param(True, 400, 400, id='closed'),
    ],
)
def test_time_entry_update_locked_by_timesheet(
    closed, updated_status, deleted_status, scenario_time_entries, admin_user, api_client
):
    from krm3.core.models import TimesheetSubmission  # noqa: PLC0415

    pk = scenario_time_entries['time_entries'][1].id
    url = reverse(
        'timesheet-api:api-time-entry-detail',
        kwargs={'pk': pk}
    )

    task: 'Task' = scenario_time_entries['tasks']['t1']
    TimesheetSubmission.objects.create(period=['2025-08-24', '2025-08-31'], resource=task.resource, closed=closed)

    response = api_client(user=admin_user).put(
        url,
        data={'date': _dt('20250824'), 'task': task.id, 'day_shift_hours': 4, 'resource': task.resource.id},
        content_type='application/json',
    )
    assert response.status_code == updated_status, response.data.get('detail')
    if response.status_code == 200:
        assert response.data['day_shift_hours'] == '4.00'

    response = api_client(user=admin_user).delete(url)
    assert response.status_code == deleted_status, response.data.get('detail')
