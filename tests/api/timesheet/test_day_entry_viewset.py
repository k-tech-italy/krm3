import logging
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django import test as django_test
from rest_framework import status

from testutils.factories import TaskFactory

from krm3.core.models import DayEntry, TaskEntry


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


@pytest.mark.parametrize(
    'entry_data',
    (
        pytest.param({'leave_hours': 2}, id='leave'),
        pytest.param({'asked_holiday': True}, id='holiday'),
        pytest.param({'is_sick': True}, id='sick'),
    ),
)
def test_creates_single_valid_day_entry(entry_data, api_client):
    entry_date = date(2024, 1, 2)
    contract = ContractFactory(period=(entry_date, None))

    response = api_client(user=contract.resource.user).post(
        reverse('timesheet-api:api-day-entry-list'),
        data={
            'day': entry_date.isoformat(),
            'resource': contract.resource_id,
            'comment': 'approved',
            **entry_data,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    day_entry = DayEntry.objects.get(
        resource=contract.resource,
        day=entry_date,
    )
    assert day_entry.comment == 'approved'
    assert day_entry.special_leave_hours == 0
    assert day_entry.special_leave_reason is None


@pytest.mark.parametrize(
    ('dates', 'expected_status'),
    (
        pytest.param(['2024-01-01'], status.HTTP_200_OK, id='one-day-at-start'),
        pytest.param(['2024-01-15'], status.HTTP_200_OK, id='one-day-within-range'),
        pytest.param(['2024-01-31'], status.HTTP_200_OK, id='one-day-at-end'),
        pytest.param(['2023-12-31'], status.HTTP_400_BAD_REQUEST, id='one-day-before-start'),
        pytest.param(['2024-02-01'], status.HTTP_400_BAD_REQUEST, id='one-day-after-end'),
        pytest.param(['2023-12-30', '2023-12-31'], status.HTTP_400_BAD_REQUEST, id='range-before-start'),
        pytest.param(['2023-12-31', '2024-01-01'], status.HTTP_400_BAD_REQUEST, id='range-overlapping-start'),
        pytest.param(['2024-02-01', '2024-02-02'], status.HTTP_400_BAD_REQUEST, id='range-after-end'),
        pytest.param(['2024-01-31', '2024-02-01'], status.HTTP_400_BAD_REQUEST, id='range-overlapping-end'),
        pytest.param(
            ['2023-12-31', *[f'2024-01-{day:02d}' for day in range(1, 32)], '2024-02-01'],
            status.HTTP_400_BAD_REQUEST,
            id='range-containing-validity-period',
        ),
        pytest.param(
            [f'2024-01-{day:02d}' for day in range(11, 16)],
            status.HTTP_200_OK,
            id='range-within-validity-period',
        ),
        pytest.param(
            [f'2024-01-{day:02d}' for day in range(1, 32) if day != 6],
            status.HTTP_200_OK,
            id='range-equal-to-validity-period',
        ),
    ),
)
def test_accepts_special_leave_only_when_reason_is_valid_for_all_dates(dates, expected_status, api_client):
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(date(2023, 12, 1), date(2024, 3, 1)))
    reason = SpecialLeaveReasonFactory(from_date=date(2024, 1, 1), to_date=date(2024, 1, 31))

    response = api_client(user=resource.user).post(
        _url(),
        data={
            'dates': dates,
            'resource': resource.pk,
            'special_leave_hours': 8,
            'special_leave_reason': reason.pk,
            'comment': 'approved',
        },
        format='json',
    )

    assert response.status_code == expected_status
    assert DayEntry.objects.filter(resource=resource).exists() is (expected_status == status.HTTP_200_OK)


@pytest.mark.parametrize(
    ('entry_data', 'expected_status'),
    (
        pytest.param({'is_sick': True}, status.HTTP_201_CREATED, id='sick'),
        pytest.param({'asked_holiday': True}, status.HTTP_201_CREATED, id='holiday'),
        pytest.param({'leave_hours': 4}, status.HTTP_201_CREATED, id='leave'),
        pytest.param({'special_leave_hours': 4}, status.HTTP_201_CREATED, id='special-leave'),
        pytest.param(
            {'leave_hours': 4, 'special_leave_hours': 4},
            status.HTTP_201_CREATED,
            id='leave-and-special-leave',
        ),
        pytest.param({'is_sick': True, 'asked_holiday': True}, status.HTTP_400_BAD_REQUEST, id='sick-and-holiday'),
        pytest.param({'is_sick': True, 'leave_hours': 4}, status.HTTP_400_BAD_REQUEST, id='sick-and-leave'),
        pytest.param(
            {'is_sick': True, 'special_leave_hours': 4},
            status.HTTP_400_BAD_REQUEST,
            id='sick-and-special-leave',
        ),
        pytest.param(
            {'asked_holiday': True, 'leave_hours': 4},
            status.HTTP_400_BAD_REQUEST,
            id='holiday-and-leave',
        ),
        pytest.param(
            {'asked_holiday': True, 'special_leave_hours': 4},
            status.HTTP_400_BAD_REQUEST,
            id='holiday-and-special-leave',
        ),
    ),
)
def test_accepts_at_most_one_absence_kind(entry_data, expected_status, api_client):
    entry_date = date(2024, 1, 2)
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(entry_date, None))
    reason = SpecialLeaveReasonFactory()
    if entry_data.get('special_leave_hours'):
        entry_data = {**entry_data, 'special_leave_reason': reason.pk}

    response = api_client(user=resource.user).post(
        _url(),
        data={'day': entry_date.isoformat(), 'resource': resource.pk, **entry_data},
        format='json',
    )

    assert response.status_code == expected_status
    assert DayEntry.objects.filter(resource=resource, day=entry_date).exists() is (
        expected_status == status.HTTP_201_CREATED
    )


def test_rejects_holiday_request_on_public_holiday(api_client):
    entry_date = date(2027, 1, 1)
    contract = ContractFactory(period=(entry_date, None))

    response = api_client(user=contract.resource.user).post(
        _url(),
        data={
            'day': entry_date.isoformat(),
            'resource': contract.resource_id,
            'asked_holiday': True,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not DayEntry.objects.filter(
        resource=contract.resource,
        day=entry_date,
    ).exists()


@pytest.mark.parametrize(
    'entry_data',
    (
        pytest.param({'is_sick': True}, id='sick'),
        pytest.param({'asked_holiday': True}, id='holiday'),
        pytest.param({'leave_hours': 4}, id='leave'),
        pytest.param({'special_leave_hours': 4}, id='special-leave'),
    ),
)
def test_accepts_day_entries_for_multiple_days(entry_data, api_client):
    dates = [date(2024, 1, day) for day in range(8, 13)]
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(dates[0], dates[-1] + timedelta(days=1)))
    if entry_data.get('special_leave_hours'):
        entry_data = {**entry_data, 'special_leave_reason': SpecialLeaveReasonFactory().pk}

    response = api_client(user=resource.user).post(
        _url(),
        data={
            'dates': [day.isoformat() for day in dates],
            'resource': resource.pk,
            'comment': 'approved',
            **entry_data,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(DayEntry.objects.filter(resource=resource).values_list('day', flat=True)) == set(dates)


def test_rejects_day_entry_when_total_hours_exceed_24(api_client):
    entry_date = date(2024, 1, 1)
    contract = ContractFactory(period=(entry_date, None))
    day_entry = DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=entry_date,
        due_hours=8,
    )
    first_task = TaskFactory(resource=contract.resource, period=contract.period)
    second_task = TaskFactory(resource=contract.resource, period=contract.period)
    TaskEntryFactory(day_entry=day_entry, task=first_task, day_shift_hours=6)
    TaskEntryFactory(day_entry=day_entry, task=second_task, day_shift_hours=2, night_shift_hours=6)
    day_entry.refresh(task_entries=None, drop_existing=False)

    response = api_client(user=contract.resource.user).post(
        _url(),
        data={
            'dates': [entry_date.isoformat()],
            'resource': contract.resource_id,
            'leave_hours': 12,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    day_entry.refresh_from_db()
    assert day_entry.leave_hours == Decimal(0)


@pytest.mark.parametrize('hours_field', ('leave_hours', 'special_leave_hours', 'rest_hours'))
def test_rejects_negative_day_entry_hours(hours_field, api_client):
    entry_date = date(2024, 1, 1)
    contract = ContractFactory(period=(entry_date, None))
    data = {
        'day': entry_date.isoformat(),
        'resource': contract.resource_id,
        hours_field: -1,
    }
    if hours_field == 'special_leave_hours':
        data['special_leave_reason'] = SpecialLeaveReasonFactory().pk

    response = api_client(user=contract.resource.user).post(_url(), data=data, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    ('entry_data', 'field', 'expected'),
    (
        pytest.param({'is_sick': True}, 'is_sick', True, id='sick'),
        pytest.param({'asked_holiday': True}, 'asked_holiday', True, id='holiday'),
        pytest.param({'leave_hours': 8}, 'leave_hours', Decimal(8), id='leave'),
        pytest.param({'rest_hours': 8}, 'rest_hours', Decimal(8), id='rest'),
    ),
)
def test_bulk_update_replaces_existing_absence(entry_data, field, expected, api_client):
    entry_date = date(2024, 1, 2)
    existing = DayEntryFactory(day=entry_date, is_sick=True)

    response = api_client(user=existing.resource.user).post(
        _url(),
        data={
            'dates': [entry_date.isoformat()],
            'resource': existing.resource_id,
            'is_sick': False,
            **entry_data,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    existing.refresh_from_db()
    assert getattr(existing, field) == expected


@pytest.mark.parametrize(
    ('entry_data', 'task_should_exist'),
    (
        pytest.param({'is_sick': True}, False, id='sick'),
        pytest.param({'asked_holiday': True}, False, id='holiday'),
        pytest.param({'leave_hours': 4}, True, id='leave'),
        pytest.param({'rest_hours': 4}, True, id='rest'),
    ),
)
def test_day_entry_absence_updates_related_tasks(entry_data, task_should_exist, api_client):
    day_entry = DayEntryFactory(due_hours=8)
    task_entry = TaskEntryFactory(day_entry=day_entry, resource=day_entry.resource, day_shift_hours=4)

    response = api_client(user=day_entry.resource.user).post(
        _url(),
        data={
            'dates': [day_entry.day.isoformat()],
            'resource': day_entry.resource_id,
            **entry_data,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert TaskEntry.objects.filter(pk=task_entry.pk).exists() is task_should_exist


@pytest.mark.skip(reason='Holiday event dispatch is not currently connected to DayEntry creation.')
@django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
def test_sends_holiday_event_when_holiday_is_logged(api_client, caplog):
    entry_date = date(2024, 1, 2)
    contract = ContractFactory(period=(entry_date, None))

    with caplog.at_level(logging.INFO):
        response = api_client(user=contract.resource.user).post(
            _url(),
            data={
                'day': entry_date.isoformat(),
                'resource': contract.resource_id,
                'asked_holiday': True,
            },
            format='json',
        )

    assert response.status_code == status.HTTP_201_CREATED
    expected_payload = {
        'resource': {'name': contract.resource.full_name, 'email': contract.resource.user.email},
        'start_date': entry_date.isoformat(),
        'end_date': entry_date.isoformat(),
    }
    assert any(
        'Event "holidays" sent' in record.message and str(expected_payload) in record.message
        for record in caplog.records
    )


@pytest.mark.skip(reason='Holiday event dispatch is not currently connected to DayEntry creation.')
@django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
def test_sends_holiday_event_with_start_and_end_dates(api_client, caplog):
    dates = [date(2024, 1, day) for day in (3, 1, 4, 2)]
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(date(2024, 1, 1), date(2024, 1, 5)))

    with caplog.at_level(logging.INFO):
        response = api_client(user=resource.user).post(
            _url(),
            data={
                'dates': [day.isoformat() for day in dates],
                'resource': resource.pk,
                'asked_holiday': True,
            },
            format='json',
        )

    assert response.status_code == status.HTTP_200_OK
    expected_payload = {
        'resource': {'name': resource.full_name, 'email': resource.user.email},
        'start_date': '2024-01-01',
        'end_date': '2024-01-04',
    }
    assert any(
        'Event "holidays" sent' in record.message and str(expected_payload) in record.message
        for record in caplog.records
    )


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

from decimal import Decimal

from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import DayEntryFactory, SpecialLeaveReasonFactory, TaskEntryFactory


def _delete_url():
    return reverse('timesheet-api:api-day-entry-delete')


def _clear_url():
    return reverse('timesheet-api:api-day-entry-clear')


def test_delete_removes_non_task_data_and_preserves_tasks(api_client):
    special_leave_reason = SpecialLeaveReasonFactory()
    day_entry = DayEntryFactory(
        bank=2,
        asked_holiday=True,
        leave_hours=3,
        special_leave_hours=2,
        special_leave_reason=special_leave_reason,
        protocol_number='12345',
        is_sick=True,
        rest_hours=1,
        comment='Remove me',
    )
    task_entry = TaskEntryFactory(
        resource=day_entry.resource,
        day_entry=day_entry,
        day_shift_hours=4,
        night_shift_hours=1,
        travel_hours=1,
        on_call_hours=2,
    )

    response = api_client(user=day_entry.resource.user).post(
        _delete_url(), data={'ids': [day_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    day_entry.refresh_from_db()
    assert day_entry.taskentry_set.get() == task_entry
    assert day_entry.bank == Decimal(0)
    assert day_entry.asked_holiday is False
    assert day_entry.leave_hours == Decimal(0)
    assert day_entry.special_leave_hours == Decimal(0)
    assert day_entry.special_leave_reason is None
    assert day_entry.protocol_number is None
    assert day_entry.is_sick is False
    assert day_entry.rest_hours == Decimal(0)
    assert day_entry.comment is None
    assert day_entry.day_hours == Decimal(4)
    assert day_entry.night_hours == Decimal(1)
    assert day_entry.travel_hours == Decimal(1)
    assert day_entry.on_call_hours == Decimal(2)


def test_delete_removes_day_entries_without_tasks(api_client):
    day_entry = DayEntryFactory(leave_hours=2, comment='Remove me')

    response = api_client(user=day_entry.resource.user).post(
        _delete_url(), data={'ids': [day_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not type(day_entry).objects.filter(pk=day_entry.pk).exists()


def test_delete_rejects_the_whole_request_when_an_entry_is_closed(api_client):
    open_entry = DayEntryFactory(leave_hours=2)
    closed_entry = DayEntryFactory(resource=open_entry.resource, leave_hours=3, closed=True)

    response = api_client(user=open_entry.resource.user).post(
        _delete_url(), data={'ids': [open_entry.pk, closed_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    open_entry.refresh_from_db()
    closed_entry.refresh_from_db()
    assert open_entry.leave_hours == Decimal(2)
    assert closed_entry.leave_hours == Decimal(3)


def test_delete_rejects_the_whole_request_when_an_entry_is_unauthorized(api_client):
    own_entry = DayEntryFactory(leave_hours=2)
    other_entry = DayEntryFactory(leave_hours=3)

    response = api_client(user=own_entry.resource.user).post(
        _delete_url(), data={'ids': [own_entry.pk, other_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    own_entry.refresh_from_db()
    other_entry.refresh_from_db()
    assert own_entry.leave_hours == Decimal(2)
    assert other_entry.leave_hours == Decimal(3)


def test_delete_requires_a_non_empty_id_list(api_client, regular_user):
    client = api_client(user=regular_user)

    missing_response = client.post(_delete_url(), data={}, format='json')
    invalid_response = client.post(_delete_url(), data={'ids': 1}, format='json')

    assert missing_response.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_response.data == {'error': 'No day entry ids provided.'}
    assert invalid_response.status_code == status.HTTP_400_BAD_REQUEST
    assert invalid_response.data == {'error': 'Day entry ids must be in a list.'}


def test_clear_deletes_day_entries_and_their_tasks(api_client):
    first_entry = DayEntryFactory()
    second_entry = DayEntryFactory(resource=first_entry.resource)
    first_task = TaskEntryFactory(resource=first_entry.resource, day_entry=first_entry)
    second_task = TaskEntryFactory(resource=second_entry.resource, day_entry=second_entry)

    response = api_client(user=first_entry.resource.user).post(
        _clear_url(), data={'ids': [first_entry.pk, second_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not type(first_entry).objects.filter(pk__in=[first_entry.pk, second_entry.pk]).exists()
    assert not type(first_task).objects.filter(pk__in=[first_task.pk, second_task.pk]).exists()


def test_clear_rejects_the_whole_request_when_an_entry_is_closed(api_client):
    open_entry = DayEntryFactory()
    closed_entry = DayEntryFactory(resource=open_entry.resource, closed=True)

    response = api_client(user=open_entry.resource.user).post(
        _clear_url(), data={'ids': [open_entry.pk, closed_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert type(open_entry).objects.filter(pk__in=[open_entry.pk, closed_entry.pk]).count() == 2


def test_clear_rejects_the_whole_request_when_an_entry_is_unauthorized(api_client):
    own_entry = DayEntryFactory()
    other_entry = DayEntryFactory()

    response = api_client(user=own_entry.resource.user).post(
        _clear_url(), data={'ids': [own_entry.pk, other_entry.pk]}, format='json'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert type(own_entry).objects.filter(pk__in=[own_entry.pk, other_entry.pk]).count() == 2


def test_clear_requires_a_non_empty_id_list(api_client, regular_user):
    client = api_client(user=regular_user)

    missing_response = client.post(_clear_url(), data={}, format='json')
    invalid_response = client.post(_clear_url(), data={'ids': 1}, format='json')

    assert missing_response.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_response.data == {'error': 'No day entry ids provided.'}
    assert invalid_response.status_code == status.HTTP_400_BAD_REQUEST
    assert invalid_response.data == {'error': 'Day entry ids must be in a list.'}

import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import DayEntryFactory


@pytest.fixture
def day_entry_scenario(resources):
    return {
        'resources': resources,
        'regular_entries': [
            DayEntryFactory(resource=resources['regular']),
            DayEntryFactory(resource=resources['regular']),
        ],
        'other_entry': DayEntryFactory(resource=resources['other']),
    }


@pytest.mark.parametrize(
    ('usr', 'visible_entries'),
    [
        pytest.param('admin', 'all', id='admin'),
        pytest.param('viewer', 'all', id='viewer'),
        pytest.param('manager', 'all', id='manager'),
        pytest.param('regular', 'regular', id='regular'),
        pytest.param('other', 'other', id='other'),
    ],
)
def test_day_entry_list_permissions(usr, visible_entries, day_entry_scenario, api_client):
    resources = day_entry_scenario['resources']
    regular_entries = day_entry_scenario['regular_entries']
    other_entry = day_entry_scenario['other_entry']

    expected_ids = {
        'all': {regular_entries[0].pk, regular_entries[1].pk, other_entry.pk},
        'regular': {regular_entries[0].pk, regular_entries[1].pk},
        'other': {other_entry.pk},
    }[visible_entries]

    url = reverse('timesheet-api:api-day-entry-list')
    response = api_client(user=resources[usr].user).get(url)

    assert response.status_code == status.HTTP_200_OK
    assert {entry['id'] for entry in response.data['results']} == expected_ids

from datetime import date

import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import ContractFactory, DayEntryFactory, ResourceFactory, SpecialLeaveReasonFactory


def _day_entry_url():
    return reverse('timesheet-api:api-day-entry-list')


def test_create_rejects_special_leave_hours_without_reason(api_client):
    resource = ResourceFactory()
    ContractFactory(resource=resource)

    response = api_client(user=resource.user).post(
        _day_entry_url(),
        data={
            'day': '2024-01-02',
            'resource': resource.pk,
            'special_leave_hours': 2,
            'special_leave_reason': None,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        'error': [
            'A special leave reason is required when special leave hours are set.'
        ]
    }


def test_create_accepts_special_leave_hours_with_reason(api_client):
    resource = ResourceFactory()
    ContractFactory(resource=resource)
    reason = SpecialLeaveReasonFactory()

    response = api_client(user=resource.user).post(
        _day_entry_url(),
        data={
            'day': '2024-01-02',
            'resource': resource.pk,
            'special_leave_hours': 2,
            'special_leave_reason': reason.pk,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_create_clears_special_leave_reason_without_hours(api_client):
    resource = ResourceFactory()
    ContractFactory(resource=resource)
    reason = SpecialLeaveReasonFactory()

    response = api_client(user=resource.user).post(
        _day_entry_url(),
        data={
            'day': '2024-01-02',
            'resource': resource.pk,
            'special_leave_hours': 0,
            'special_leave_reason': reason.pk,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['special_leave_reason'] is None


def test_update_clears_special_leave_reason_when_hours_are_removed(api_client):
    resource = ResourceFactory()
    reason = SpecialLeaveReasonFactory()
    entry = DayEntryFactory(
        resource=resource,
        day=date(2024, 1, 2),
        special_leave_hours=2,
        special_leave_reason=reason,
    )

    response = api_client(user=resource.user).post(
        _day_entry_url(),
        data={
            'dates': ['2024-01-02'],
            'resource': resource.pk,
            'special_leave_hours': 0,
        },
        format='json',
    )

    entry.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert entry.special_leave_hours == 0
    assert entry.special_leave_reason is None


def test_update_reason_uses_existing_special_leave_hours(api_client):
    resource = ResourceFactory()
    old_reason = SpecialLeaveReasonFactory()
    new_reason = SpecialLeaveReasonFactory()
    entry = DayEntryFactory(
        resource=resource,
        day=date(2024, 1, 2),
        special_leave_hours=2,
        special_leave_reason=old_reason,
    )

    response = api_client(user=resource.user).post(
        _day_entry_url(),
        data={
            'dates': ['2024-01-02'],
            'resource': resource.pk,
            'special_leave_reason': new_reason.pk,
        },
        format='json',
    )

    entry.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert entry.special_leave_hours == 2
    assert entry.special_leave_reason == new_reason
