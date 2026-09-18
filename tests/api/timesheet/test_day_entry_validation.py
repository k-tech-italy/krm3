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
        'error': 'A special leave reason is required when special leave hours are set.'
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


def test_update_rejects_removing_reason_while_special_leave_hours_remain(api_client):
    reason = SpecialLeaveReasonFactory()
    day_entry = DayEntryFactory(special_leave_hours=2, special_leave_reason=reason)

    response = api_client(user=day_entry.resource.user).patch(
        reverse('timesheet-api:api-day-entry-detail', args=[day_entry.pk]),
        data={'special_leave_reason': None},
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        'error': 'A special leave reason is required when special leave hours are set.'
    }


def test_update_accepts_zero_special_leave_hours_without_reason(api_client):
    reason = SpecialLeaveReasonFactory()
    day_entry = DayEntryFactory(special_leave_hours=2, special_leave_reason=reason)

    response = api_client(user=day_entry.resource.user).patch(
        reverse('timesheet-api:api-day-entry-detail', args=[day_entry.pk]),
        data={'special_leave_hours': 0, 'special_leave_reason': None},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
