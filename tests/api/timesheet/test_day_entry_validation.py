import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import ContractFactory, ResourceFactory, SpecialLeaveReasonFactory


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
