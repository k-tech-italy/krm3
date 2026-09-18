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
