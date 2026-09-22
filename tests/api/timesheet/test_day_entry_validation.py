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
        day='2024-01-02',
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
        day='2024-01-02',
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
