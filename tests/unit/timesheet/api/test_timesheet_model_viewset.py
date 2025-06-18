import typing

from testutils.factories import (
    ResourceFactory,
    UserFactory,
)
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import Timesheet
from testutils.permissions import add_permissions

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource


class TestTimesheetModelAPIListView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-timesheet-model-list')

    def test_save_own(self, api_client, regular_user):
        resource: Resource = ResourceFactory(user=regular_user)
        response = api_client(user=regular_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Timesheet.objects.filter(id=response.data['id']).exists()

    def test_manager_save_other(self, api_client, regular_user):
        manager = UserFactory()

        add_permissions(manager, 'core.manage_any_timesheet')

        resource: Resource = ResourceFactory(user=regular_user)

        response = api_client(user=manager).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Timesheet.objects.filter(id=response.data['id']).exists()

    def test_admin_save(self, api_client, admin_user):
        resource: Resource = ResourceFactory()
        response = api_client(user=admin_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Timesheet.objects.filter(id=response.data['id']).exists()

    def test_unauthorised_other(self, api_client, regular_user):
        user = UserFactory()
        resource: Resource = ResourceFactory(user=regular_user)

        response = api_client(user=user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
