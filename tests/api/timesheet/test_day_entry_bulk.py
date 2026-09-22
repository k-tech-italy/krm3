from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import DayEntryFactory, SpecialLeaveReasonFactory, TaskEntryFactory


def _url():
    return reverse('timesheet-api:api-day-entry-list')


def test_bulk_creates_and_updates_day_entries_in_one_request(api_client):
    existing_entry = DayEntryFactory(day=date(2026, 9, 21), leave_hours=2)

    response = api_client(user=existing_entry.resource.user).post(
        _url(),
        data={
            'resource': existing_entry.resource_id,
            'dates': ['2026-09-21', '2026-09-22'],
            'leave_hours': 4,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    entries = type(existing_entry).objects.filter(resource=existing_entry.resource).order_by('day')
    assert list(entries.values_list('day', 'leave_hours')) == [
        (existing_entry.day, Decimal('4.00')),
        (existing_entry.day.replace(day=22), Decimal('4.00')),
    ]


def test_bulk_update_allows_bank_deposit_that_leaves_hours_above_schedule(api_client):
    existing_entry = DayEntryFactory(day_hours=11, due_hours=8)

    response = api_client(user=existing_entry.resource.user).post(
        _url(),
        data={
            'resource': existing_entry.resource_id,
            'dates': [existing_entry.day.isoformat()],
            'bank': 2,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    existing_entry.refresh_from_db()
    assert existing_entry.bank == Decimal('2.00')


@pytest.mark.parametrize('absence_field', ('leave_hours', 'rest_hours', 'special_leave_hours'))
def test_bulk_update_rejects_bank_deposit_during_absence(api_client, absence_field):
    existing_entry = DayEntryFactory(day_hours=11, due_hours=8)
    data = {
        'resource': existing_entry.resource_id,
        'dates': [existing_entry.day.isoformat()],
        'bank': 2,
        absence_field: 1,
    }
    if absence_field == 'special_leave_hours':
        data['special_leave_reason'] = SpecialLeaveReasonFactory().pk

    response = api_client(user=existing_entry.resource.user).post(
        _url(),
        data=data,
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    existing_entry.refresh_from_db()
    assert existing_entry.bank == Decimal('0.00')
    assert getattr(existing_entry, absence_field) == Decimal('0.00')


def test_bulk_holiday_deletes_tasks_and_refreshes_day_entry(api_client):
    day_entry = DayEntryFactory(
        day_hours=4,
        night_hours=1,
        travel_hours=2,
        on_call_hours=3,
        overtime_hours=1,
        meal_voucher=1,
    )
    task_entry = TaskEntryFactory(
        resource=day_entry.resource,
        day_entry=day_entry,
        day_shift_hours=4,
        night_shift_hours=1,
        travel_hours=2,
        on_call_hours=3,
    )

    response = api_client(user=day_entry.resource.user).post(
        _url(),
        data={
            'resource': day_entry.resource_id,
            'dates': [day_entry.day.isoformat()],
            'asked_holiday': True,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert not type(task_entry).objects.filter(pk=task_entry.pk).exists()
    day_entry.refresh_from_db()
    assert day_entry.asked_holiday is True
    assert day_entry.day_hours == Decimal('0.00')
    assert day_entry.night_hours == Decimal('0.00')
    assert day_entry.travel_hours == Decimal('0.00')
    assert day_entry.on_call_hours == Decimal('0.00')
    assert day_entry.overtime_hours == Decimal('0.00')
    assert day_entry.meal_voucher == 0


def test_bulk_sickness_deletes_tasks(api_client):
    day_entry = DayEntryFactory()
    task_entry = TaskEntryFactory(resource=day_entry.resource, day_entry=day_entry)

    response = api_client(user=day_entry.resource.user).post(
        _url(),
        data={
            'resource': day_entry.resource_id,
            'dates': [day_entry.day.isoformat()],
            'is_sick': True,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert not type(task_entry).objects.filter(pk=task_entry.pk).exists()


def test_bulk_rejects_all_changes_when_an_entry_is_closed(api_client):
    closed_entry = DayEntryFactory(day=date(2026, 9, 22), leave_hours=2, closed=True)

    response = api_client(user=closed_entry.resource.user).post(
        _url(),
        data={
            'resource': closed_entry.resource_id,
            'dates': ['2026-09-21', '2026-09-22'],
            'leave_hours': 4,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not type(closed_entry).objects.filter(resource=closed_entry.resource, day='2026-09-21').exists()
    closed_entry.refresh_from_db()
    assert closed_entry.leave_hours == Decimal('2.00')
