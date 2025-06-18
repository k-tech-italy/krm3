import typing

import pytest

from testutils.factories import (
    ResourceFactory,
    UserFactory,
    TimesheetFactory,
)
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import Timesheet
from testutils.permissions import add_permissions

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource


@pytest.fixture
def manager():
    manager = UserFactory()
    add_permissions(manager, 'core.manage_any_timesheet')
    return manager


class TestTimesheetModelAPIListView:
    @staticmethod
    def url(*args):
        if args:
            return reverse('timesheet-api:api-timesheet-model-detail', args=args)
        return reverse('timesheet-api:api-timesheet-model-list')

    @pytest.mark.parametrize(
        'who, result',
        [
            pytest.param('regular', 'own', id='regular'),
            pytest.param('manager', 'full', id='manager'),
            pytest.param('admin', 'full', id='admin'),
        ],
    )
    def test_write(self, who, result, api_client, regular_user, manager, admin_user):
        match who:
            case 'manager':
                user = manager
            case 'admin':
                user = admin_user
            case 'regular':
                user = regular_user

        resource: Resource = ResourceFactory(user=regular_user)
        response = api_client(user=user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        obj_id = response.data['id']
        assert response.status_code == status.HTTP_201_CREATED
        assert list(Timesheet.objects.values_list('id', flat=True)) == [obj_id]

        response = api_client(user=user).put(
            self.url(obj_id), data={'resource': resource.pk, 'period': ('2024-01-08', '2024-01-14')}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert Timesheet.objects.count() == 1

        response = api_client(user=user).delete(self.url(obj_id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Timesheet.objects.count() == 0

    def test_unauthorised_other(self, api_client, regular_user):
        user = UserFactory()
        resource: Resource = ResourceFactory(user=regular_user)

        response = api_client(user=user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        timesheet: Timesheet = TimesheetFactory()
        ResourceFactory(user=user)
        response = api_client(user=user).put(
            self.url(timesheet.resource_id),
            data={'resource': resource.pk, 'period': ('2024-01-08', '2024-01-14')},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        'who, result',
        [
            pytest.param('regular', 'own', id='regular'),
            pytest.param('manager', 'full', id='manager'),
            pytest.param('admin', 'full', id='admin'),
        ],
    )
    def test_retrieve(self, who, result, api_client, regular_user, manager, admin_user):
        match who:
            case 'manager':
                user = manager
            case 'admin':
                user = admin_user
            case 'regular':
                user = regular_user

        resource: Resource = ResourceFactory(user=regular_user)
        own_ts = TimesheetFactory(resource=resource)
        other_ts = TimesheetFactory()
        expected = [own_ts.id] if result == 'own' else [own_ts.id, other_ts.id]

        response = api_client(user=user).get(self.url())
        assert response.status_code == status.HTTP_200_OK
        assert [r['id'] for r in response.data['results']] == expected
