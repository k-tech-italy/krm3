import json
from datetime import date

import pytest
from constance.test import override_config
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TaskEntry
from testutils.factories import ContractFactory, DayEntryFactory, TaskFactory


def _url():
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
        _url(),
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
        _url(),
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
        _url(),
        data=_payload(task, weekend),
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        'error': (
            'The selected dates are non-working days: 2026-09-12, 2026-09-13. '
            'Add them individually if needed.'
        )
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
        _url(),
        data=_payload(task, [monday, tuesday]),
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(
        TaskEntry.objects.filter(task=task).values_list('day_entry__day', flat=True)
    ) == {monday}
