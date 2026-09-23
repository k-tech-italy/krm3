import json
from datetime import date

import pytest
from constance.test import override_config
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TaskEntry
from testutils.factories import ContractFactory, DayEntryFactory, TaskFactory


def _non_working_days_url():
    return reverse('timesheet-api:api-task-entry-list')


def _payload(task, dates):
    return {
        'resourceId': task.resource_id,
        'taskId': task.pk,
        'dates': [day.isoformat() for day in dates],
        'dayShiftHours': 8,
    }


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps(
        {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}
    )
)
def test_allows_single_non_working_day(api_client):
    task = TaskFactory(period=(date(2026, 9, 1), date(2026, 10, 1)), contract=True)
    sunday = date(2026, 9, 13)

    response = api_client(user=task.resource.user).post(
        _non_working_days_url(),
        data=_payload(task, [sunday]),
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert TaskEntry.objects.filter(
        task=task,
        day_entry__day=sunday,
    ).exists()


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps(
        {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}
    )
)
def test_skips_non_working_days_in_mixed_multi_date_request(api_client):
    task = TaskFactory(period=(date(2026, 9, 1), date(2026, 10, 1)), contract=True)
    monday = date(2026, 9, 7)
    weekend = [date(2026, 9, 12), date(2026, 9, 13)]

    response = api_client(user=task.resource.user).post(
        _non_working_days_url(),
        data=_payload(task, [monday, *weekend]),
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(
        TaskEntry.objects.filter(task=task).values_list('day_entry__day', flat=True)
    ) == {monday}


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps(
        {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}
    )
)
def test_rejects_multi_date_request_when_all_days_are_non_working(api_client):
    task = TaskFactory(period=(date(2026, 9, 1), date(2026, 10, 1)), contract=True)
    weekend = [date(2026, 9, 12), date(2026, 9, 13)]

    response = api_client(user=task.resource.user).post(
        _non_working_days_url(),
        data=_payload(task, weekend),
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        'error': [
            'The selected dates are non-working days: 2026-09-12, 2026-09-13. '
            'Add them individually if needed.'
        ]
    }
    assert not TaskEntry.objects.filter(task=task).exists()


@pytest.mark.parametrize(
    'day_entry_data',
    (
        pytest.param({'asked_holiday': True}, id='asked-holiday'),
        pytest.param({'is_holiday': True}, id='holiday'),
        pytest.param({'is_sick': True}, id='sick'),
    ),
)
def test_skips_absence_in_mixed_multi_date_request(api_client, day_entry_data):
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 10, 1)))
    task = TaskFactory(resource=contract.resource, period=contract.period)
    monday = date(2026, 9, 7)
    tuesday = date(2026, 9, 8)
    DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=tuesday,
        due_hours=8,
        **day_entry_data,
    )

    response = api_client(user=task.resource.user).post(
        _non_working_days_url(),
        data=_payload(task, [monday, tuesday]),
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(
        TaskEntry.objects.filter(task=task).values_list('day_entry__day', flat=True)
    ) == {monday}

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import ResourceFactory, TaskEntryFactory, TimesheetSubmissionFactory

from krm3.core.models import DayEntry, TaskEntry


def _task_entry_clear_url():
    return reverse('timesheet-api:api-task-entry-clear')


def test_rejects_empty_list_of_task_entry_ids(admin_user, api_client):
    response = api_client(user=admin_user).post(_task_entry_clear_url(), data={}, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_rejects_task_entry_ids_not_in_a_list(admin_user, api_client):
    entry = TaskEntryFactory(day_entry=True)

    response = api_client(user=admin_user).post(_task_entry_clear_url(), data={'ids': entry.pk}, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_rejects_clearing_task_entries_from_closed_timesheet(admin_user, api_client):
    entry = TaskEntryFactory(date=date(2024, 1, 2))
    TimesheetSubmissionFactory(
        resource=entry.day_entry.resource,
        period=(entry.day_entry.day, entry.day_entry.day + timedelta(days=1)),
        closed=True,
    )

    response = api_client(user=admin_user).post(_task_entry_clear_url(), data={'ids': [entry.pk]}, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert TaskEntry.objects.filter(pk=entry.pk).exists()


def test_admin_can_clear_any_task_entries(admin_user, api_client):
    first_entry = TaskEntryFactory(date=date(2024, 1, 1))
    second_entry = TaskEntryFactory(date=date(2024, 1, 2))
    entry_ids = [first_entry.pk, second_entry.pk]
    day_entry_ids = [first_entry.day_entry_id, second_entry.day_entry_id]

    response = api_client(user=admin_user).post(_task_entry_clear_url(), data={'ids': entry_ids}, format='json')

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not TaskEntry.objects.filter(pk__in=entry_ids).exists()
    assert not DayEntry.objects.filter(pk__in=day_entry_ids).exists()


@pytest.mark.parametrize(
    ('permissions', 'expected_status'),
    [
        pytest.param([], status.HTTP_403_FORBIDDEN, id='no-permissions'),
        pytest.param(
            ['manage_any_project'],
            status.HTTP_403_FORBIDDEN,
            id='project-manager-without-timesheet-permissions',
        ),
        pytest.param(
            ['view_any_project'],
            status.HTTP_403_FORBIDDEN,
            id='project-viewer-without-timesheet-permissions',
        ),
        pytest.param(
            ['view_any_project', 'view_any_timesheet'],
            status.HTTP_403_FORBIDDEN,
            id='project-viewer-and-timesheet-viewer',
        ),
        pytest.param(
            ['view_any_project', 'manage_any_timesheet'],
            status.HTTP_204_NO_CONTENT,
            id='project-viewer-and-timesheet-manager',
        ),
        pytest.param(
            ['manage_any_project', 'view_any_timesheet'],
            status.HTTP_403_FORBIDDEN,
            id='project-manager-and-timesheet-viewer',
        ),
        pytest.param(
            ['manage_any_project', 'manage_any_timesheet'],
            status.HTTP_204_NO_CONTENT,
            id='project-manager-and-timesheet-manager',
        ),
    ],
)
def test_clear_permissions_for_entries_owned_by_different_users(
    permissions,
    expected_status,
    regular_user,
    api_client,
):
    own_resource = ResourceFactory(user=regular_user)
    other_resource = ResourceFactory()
    own_entry = TaskEntryFactory(resource=own_resource, date=date(2024, 1, 1))
    other_entry = TaskEntryFactory(resource=other_resource, date=date(2024, 1, 1))
    entry_ids = [own_entry.pk, other_entry.pk]

    for permission in permissions:
        regular_user.user_permissions.add(Permission.objects.get(codename=permission))

    response = api_client(user=regular_user).post(_task_entry_clear_url(), data={'ids': entry_ids}, format='json')

    assert response.status_code == expected_status
    assert TaskEntry.objects.filter(pk__in=entry_ids).exists() is (
        expected_status != status.HTTP_204_NO_CONTENT
    )

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import TaskFactory

from krm3.core.models import TaskEntry


def test_creates_task_entry_and_parent_day_entry(resource, api_client):
    task = TaskFactory(contract=True, resource=resource)
    entry_date = date(2026, 7, 1)
    url = reverse('timesheet-api:api-task-entry-list')

    response = api_client(user=resource.user).post(
        url,
        data={
            'resource_id': resource.pk,
            'task_id': task.pk,
            'dates': [entry_date.isoformat()],
            'day_shift_hours': 4,
            'night_shift_hours': 3,
            'travel_hours': 2,
            'on_call_hours': 1,
            'comment': 'Task entry comment',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.data) == 1

    task_entry = TaskEntry.objects.select_related('day_entry').get()
    assert response.data[0]['id'] == task_entry.pk
    assert response.data[0]['task'] == task.pk
    assert response.data[0]['day_entry'] == task_entry.day_entry_id
    assert Decimal(response.data[0]['day_shift_hours']) == Decimal(4)
    assert Decimal(response.data[0]['night_shift_hours']) == Decimal(3)
    assert Decimal(response.data[0]['travel_hours']) == Decimal(2)
    assert Decimal(response.data[0]['on_call_hours']) == Decimal(1)
    assert response.data[0]['comment'] == 'Task entry comment'

    assert task_entry.task == task
    assert task_entry.day_shift_hours == Decimal(4)
    assert task_entry.night_shift_hours == Decimal(3)
    assert task_entry.travel_hours == Decimal(2)
    assert task_entry.on_call_hours == Decimal(1)
    assert task_entry.comment == 'Task entry comment'
    assert task_entry.day_entry.day == entry_date
    assert task_entry.day_entry.resource == resource
    assert task_entry.day_entry.day_hours == Decimal(4)
    assert task_entry.day_entry.night_hours == Decimal(3)
    assert task_entry.day_entry.travel_hours == Decimal(2)
    assert task_entry.day_entry.on_call_hours == Decimal(1)


@pytest.mark.parametrize(
    'covered_hours',
    (
        pytest.param({'leave_hours': 4}, id='leave'),
        pytest.param({'special_leave_hours': 4}, id='special_leave'),
        pytest.param({'rest_hours': 4}, id='rest'),
        pytest.param({'bank': -4}, id='bank-withdrawal'),
    ),
)
@pytest.mark.parametrize(
    ('working_hours', 'expected_status'),
    (
        pytest.param(4, status.HTTP_201_CREATED, id='available-hours'),
        pytest.param(5, status.HTTP_400_BAD_REQUEST, id='above-available-hours'),
    ),
)
def test_limits_working_hours_when_due_hours_are_partially_covered(
    covered_hours,
    working_hours,
    expected_status,
    api_client,
):
    entry_date = date(2024, 1, 1)
    contract = ContractFactory(period=(entry_date, None))
    task = TaskFactory(
        resource=contract.resource,
        period=(entry_date, None),
    )
    DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
        **covered_hours,
    )

    response = api_client(user=contract.resource.user).post(
        reverse('timesheet-api:api-task-entry-list'),
        data={
            'dates': [entry_date.isoformat()],
            'day_shift_hours': working_hours,
            'task_id': task.pk,
            'resource_id': contract.resource_id,
        },
        format='json',
    )

    assert response.status_code == expected_status


def test_counts_working_hours_from_other_tasks_against_available_hours(api_client):
    entry_date = date(2024, 1, 1)
    contract = ContractFactory(period=(entry_date, None))
    day_entry = DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
        leave_hours=4,
    )
    existing_task = TaskFactory(
        resource=contract.resource,
        period=(entry_date, None),
    )
    TaskEntryFactory(
        day_entry=day_entry,
        task=existing_task,
        day_shift_hours=2,
    )
    new_task = TaskFactory(
        resource=contract.resource,
        period=(entry_date, None),
    )

    response = api_client(user=contract.resource.user).post(
        reverse('timesheet-api:api-task-entry-list'),
        data={
            'dates': [entry_date.isoformat()],
            'day_shift_hours': 3,
            'task_id': new_task.pk,
            'resource_id': contract.resource_id,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not TaskEntry.objects.filter(
        task=new_task,
        day_entry__day=entry_date,
    ).exists()


def _task_entry_create_url():
    return reverse('timesheet-api:api-task-entry-list')


def _post_task_entry(api_client, task, entry_date, **data):
    return api_client(user=task.resource.user).post(
        _task_entry_create_url(),
        data={
            'dates': [entry_date.isoformat()],
            'task_id': task.pk,
            'resource_id': task.resource_id,
            'day_shift_hours': 0,
            **data,
        },
        format='json',
    )


def test_rejects_task_entry_without_hours(api_client):
    entry_date = date(2024, 1, 1)
    task = TaskFactory(period=(entry_date, None), contract=True)

    response = _post_task_entry(api_client, task, entry_date, day_shift_hours=0)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not TaskEntry.objects.filter(task=task, day_entry__day=entry_date).exists()


@pytest.mark.parametrize(
    ('day_entry_data', 'same_task_hours', 'other_task_hours', 'expected_hours'),
    (
        pytest.param({}, 0, 0, 8, id='empty-day'),
        pytest.param({}, 3, 0, 8, id='same-task-partial'),
        pytest.param({}, 10, 0, 10, id='same-task-overtime'),
        pytest.param({'leave_hours': 2}, 2, 0, 6, id='task-and-leave'),
        pytest.param({'rest_hours': 2}, 2, 0, 6, id='task-and-rest'),
        pytest.param({'leave_hours': 4}, 0, 0, 4, id='half-day-leave'),
        pytest.param({'rest_hours': 4}, 0, 0, 4, id='half-day-rest'),
        pytest.param({'bank': -4}, 0, 0, 4, id='bank-withdrawal'),
        pytest.param({'bank': -4}, 2, 0, 4, id='task-and-bank-withdrawal'),
        pytest.param({'rest_hours': 2, 'bank': -2}, 0, 0, 4, id='rest-and-bank-withdrawal'),
        pytest.param({}, 2, 4, 4, id='task-and-travel'),
        pytest.param({'leave_hours': 2, 'rest_hours': 2}, 2, 0, 4, id='leave-rest-task'),
    ),
)
def test_autofill_task_entry(
    day_entry_data,
    same_task_hours,
    other_task_hours,
    expected_hours,
    api_client,
):
    entry_date = date(2024, 1, 8)
    contract = ContractFactory(
        period=(entry_date, None),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    task = TaskFactory(resource=contract.resource, period=contract.period)
    day_entry = DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
        **day_entry_data,
    )
    if same_task_hours:
        TaskEntryFactory(day_entry=day_entry, task=task, day_shift_hours=same_task_hours)
    if other_task_hours:
        other_task = TaskFactory(resource=contract.resource, period=contract.period)
        TaskEntryFactory(
            day_entry=day_entry,
            task=other_task,
            day_shift_hours=0,
            travel_hours=other_task_hours,
        )
    day_entry.refresh(task_entries=None, drop_existing=False)

    response = _post_task_entry(api_client, task, entry_date, autofill=True)

    assert response.status_code == status.HTTP_201_CREATED
    entry = TaskEntry.objects.filter(task=task, day_entry=day_entry).first()
    assert entry is not None
    assert entry.day_shift_hours == Decimal(str(expected_hours))


@pytest.mark.parametrize(
    'day_entry_data',
    (
        pytest.param({'is_sick': True}, id='sick'),
        pytest.param({'asked_holiday': True}, id='holiday'),
    ),
)
def test_autofill_skips_full_absence_day(day_entry_data, api_client):
    entry_date = date(2024, 1, 8)
    contract = ContractFactory(period=(entry_date, None))
    task = TaskFactory(resource=contract.resource, period=contract.period)
    DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
        **day_entry_data,
    )

    response = _post_task_entry(api_client, task, entry_date, autofill=True)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not TaskEntry.objects.filter(task=task, day_entry__day=entry_date).exists()


@pytest.mark.parametrize(
    ('same_task_hours', 'other_task_hours', 'leave_hours', 'expected_hours'),
    (
        pytest.param(0, 0, 0, 8, id='empty-day'),
        pytest.param(3, 3, 0, 5, id='same-task-partial'),
        pytest.param(4, 4, 0, 4, id='two-tasks-full-day'),
        pytest.param(2, 2, 2, 4, id='two-tasks-and-leave'),
        pytest.param(0, 2.5, 4, 1.5, id='half-day-leave-and-other-task'),
    ),
)
def test_autofill_counts_entries_from_multiple_tasks(
    same_task_hours,
    other_task_hours,
    leave_hours,
    expected_hours,
    api_client,
):
    entry_date = date(2024, 1, 8)
    contract = ContractFactory(period=(entry_date, None))
    task = TaskFactory(resource=contract.resource, period=contract.period)
    other_task = TaskFactory(resource=contract.resource, period=contract.period)
    day_entry = DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
        leave_hours=leave_hours,
    )
    if same_task_hours:
        TaskEntryFactory(day_entry=day_entry, task=task, day_shift_hours=same_task_hours)
    if other_task_hours:
        TaskEntryFactory(day_entry=day_entry, task=other_task, day_shift_hours=other_task_hours)
    day_entry.refresh(task_entries=None, drop_existing=False)

    response = _post_task_entry(api_client, task, entry_date, autofill=True)

    assert response.status_code == status.HTTP_201_CREATED
    assert TaskEntry.objects.get(task=task, day_entry=day_entry).day_shift_hours == Decimal(str(expected_hours))


@pytest.mark.parametrize(
    'hours_data',
    (
        pytest.param({'day_shift_hours': 8}, id='day-shift'),
        pytest.param(
            {'day_shift_hours': 4, 'travel_hours': 2, 'on_call_hours': 3, 'night_shift_hours': 1},
            id='all-task-hours',
        ),
    ),
)
@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps(
        {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8}
    )
)
def test_accepts_task_entries_for_multiple_days(hours_data, api_client):
    dates = [date(2024, 1, day) for day in range(7, 12)]
    task = TaskFactory(period=(dates[0], dates[-1] + timedelta(days=1)), contract=True)

    response = api_client(user=task.resource.user).post(
        _task_entry_create_url(),
        data={
            'dates': [day.isoformat() for day in dates],
            'task_id': task.pk,
            'resource_id': task.resource_id,
            **hours_data,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(TaskEntry.objects.filter(task=task).values_list('day_entry__day', flat=True)) == set(dates)


@pytest.mark.parametrize(
    'hours_data',
    (
        pytest.param({'day_shift_hours': 17}, id='day-shift'),
        pytest.param({'night_shift_hours': 9}, id='night-shift'),
        pytest.param({'day_shift_hours': 16, 'night_shift_hours': 8, 'travel_hours': 1}, id='total'),
    ),
)
def test_rejects_task_entry_above_daily_hour_limits(hours_data, api_client):
    entry_date = date(2024, 1, 1)
    task = TaskFactory(period=(entry_date, None), contract=True)

    response = _post_task_entry(api_client, task, entry_date, **hours_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not TaskEntry.objects.filter(task=task, day_entry__day=entry_date).exists()


def test_upsert_replaces_existing_task_entry_hours(api_client):
    entry_date = date(2024, 1, 1)
    task = TaskFactory(period=(entry_date, None), contract=True)
    existing = TaskEntryFactory(resource=task.resource, date=entry_date, task=task, day_shift_hours=16)

    response = _post_task_entry(api_client, task, entry_date, day_shift_hours=10)

    assert response.status_code == status.HTTP_201_CREATED
    existing.refresh_from_db()
    assert existing.day_shift_hours == Decimal(10)
    assert TaskEntry.objects.filter(task=task, day_entry__day=entry_date).count() == 1


@pytest.mark.parametrize(
    'hours_field',
    ('day_shift_hours', 'night_shift_hours', 'travel_hours', 'on_call_hours'),
)
def test_rejects_negative_task_entry_hours(hours_field, api_client):
    entry_date = date(2024, 1, 1)
    task = TaskFactory(period=(entry_date, None), contract=True)

    response = _post_task_entry(api_client, task, entry_date, **{hours_field: -1})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    'hours_field',
    ('day_shift_hours', 'night_shift_hours', 'travel_hours'),
)
def test_upsert_replaces_hours_for_same_task_and_day(hours_field, api_client):
    entry_date = date(2024, 1, 2)
    task = TaskFactory(period=(entry_date, None), contract=True)
    existing = TaskEntryFactory(resource=task.resource, date=entry_date, task=task, day_shift_hours=4)

    response = _post_task_entry(api_client, task, entry_date, **{hours_field: 4})

    assert response.status_code == status.HTTP_201_CREATED
    existing.refresh_from_db()
    assert getattr(existing, hours_field) == Decimal(4)
    if hours_field != 'day_shift_hours':
        assert existing.day_shift_hours == Decimal(0)

import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.date_utils import _dt
from testutils.factories import TaskFactory, TaskEntryFactory

from krm3.core.models import TaskEntry


def test_task_entry_list_rejects_anonymous_user(api_client):
    url = reverse('timesheet-api:api-task-entry-list')

    response = api_client().get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.fixture
def task_entry_scenario(resources):
    t1 = TaskFactory(resource=resources['admin'], contract=True)
    t2 = TaskFactory(resource=resources['regular'], contract=True)  # other resource
    return {
        'resources': resources,
        'tasks': {
            't1': t1,
            't2': t2,
        },
        'task_entries': {
            1: TaskEntryFactory(resource=resources['admin'], date=_dt('20250824'), task=t1, day_shift_hours=2),
            2: TaskEntryFactory(resource=resources['admin'], date=_dt('20250825'), task=t1, day_shift_hours=2),
            3: TaskEntryFactory(resource=resources['admin'], date=_dt('20250826'), task=t1, day_shift_hours=2),
            4: TaskEntryFactory(resource=resources['admin'], date=_dt('20250827'), task=t1, day_shift_hours=2),
            5: TaskEntryFactory(resource=resources['admin'], date=_dt('20250828'), task=t1, day_shift_hours=2),
            6: TaskEntryFactory(resource=resources['admin'], date=_dt('20250829'), task=t1, day_shift_hours=2),
            7: TaskEntryFactory(resource=resources['regular'], date=_dt('20250827'), task=t2, day_shift_hours=2),
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
def test_task_entry_list_permissions(usr: str, num: int, task_entry_scenario, api_client):
    requestor = task_entry_scenario['resources'][usr].user
    url = reverse('timesheet-api:api-task-entry-list')
    response = api_client(user=requestor).get(url)
    assert response.status_code == status.HTTP_200_OK, response.data.get('detail')
    assert response.data['count'] == num


@pytest.mark.parametrize(
    'usr, expected',
    [
        pytest.param('admin', 200, id='admin'),
        pytest.param('viewer', 200, id='viewer'),
        pytest.param('manager', 200, id='manager'),
        pytest.param('regular', 404, id='regular'),
    ],
)
def test_task_entry_retrieve_permissions(usr: str, expected: int, task_entry_scenario, api_client):
    requestor = task_entry_scenario['resources'][usr].user
    url = reverse(
        'timesheet-api:api-task-entry-detail',
        kwargs={'pk': task_entry_scenario['task_entries'][1].id},
    )
    response = api_client(user=requestor).get(url)
    assert response.status_code == expected, response.data.get('detail')


@pytest.mark.parametrize(
    ('usr', 'expected_status', 'should_create'),
    [
        pytest.param('admin', status.HTTP_201_CREATED, True, id='admin'),
        pytest.param('viewer', status.HTTP_403_FORBIDDEN, False, id='viewer'),
        pytest.param('manager', status.HTTP_201_CREATED, True, id='manager'),
        pytest.param('regular', status.HTTP_403_FORBIDDEN, False, id='regular'),
    ],
)
def test_task_entry_create_permissions(
    usr: str,
    expected_status: int,
    should_create: bool,
    task_entry_scenario,
    api_client,
):
    requestor = task_entry_scenario['resources'][usr].user
    url = reverse('timesheet-api:api-task-entry-list')
    task = task_entry_scenario['tasks']['t1']
    resource = task.resource
    target_date = _dt('20250830')

    response = api_client(user=requestor).post(
        url,
        data={
            'dates': [target_date],
            'task_id': task.id,
            'day_shift_hours': 2,
            'resource_id': resource.id,
        },
        content_type='application/json',
    )
    assert response.status_code == expected_status, response.data.get('detail')
    assert TaskEntry.objects.filter(
        day_entry__day=target_date,
        day_entry__resource=resource,
        task=task,
    ).exists() is should_create


@pytest.mark.parametrize(
    ('usr', 'expected_status', 'expected_hours'),
    [
        pytest.param('admin', status.HTTP_201_CREATED, 4, id='admin'),
        pytest.param('viewer', status.HTTP_403_FORBIDDEN, 2, id='viewer'),
        pytest.param('manager', status.HTTP_201_CREATED, 4, id='manager'),
        pytest.param('regular', status.HTTP_403_FORBIDDEN, 2, id='regular'),
    ],
)
def test_task_entry_upsert_permissions(
    usr: str,
    expected_status: int,
    expected_hours: int,
    task_entry_scenario,
    api_client,
):
    existing_entry = task_entry_scenario['task_entries'][1]
    requestor = task_entry_scenario['resources'][usr].user
    url = reverse('timesheet-api:api-task-entry-list')

    response = api_client(user=requestor).post(
        url,
        data={
            'dates': [existing_entry.day_entry.day],
            'task_id': existing_entry.task_id,
            'day_shift_hours': 4,
            'resource_id': existing_entry.day_entry.resource_id,
        },
        content_type='application/json',
    )

    assert response.status_code == expected_status, response.data.get('detail')
    existing_entry.refresh_from_db()
    assert existing_entry.day_shift_hours == expected_hours
    assert TaskEntry.objects.count() == 7


@pytest.mark.parametrize(
    'usr, expected',
    [
        pytest.param('admin', 204, id='admin'),
        pytest.param('viewer', 403, id='viewer'),
        pytest.param('manager', 204, id='manager'),
        pytest.param('regular', 404, id='regular'),
    ],
)
def test_task_entry_delete_permissions(usr: str, expected: int, task_entry_scenario, api_client):
    pk = task_entry_scenario['task_entries'][1].id
    url = reverse('timesheet-api:api-task-entry-detail', kwargs={'pk': pk})
    requestor = task_entry_scenario['resources'][usr].user

    response = api_client(user=requestor).delete(url)
    assert response.status_code == expected, response.data.get('detail')

    assert TaskEntry.objects.filter(pk=pk).exists() is (expected != status.HTTP_204_NO_CONTENT)
