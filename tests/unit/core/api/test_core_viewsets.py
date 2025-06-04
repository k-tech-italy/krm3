from django.contrib.auth.models import Permission
import pytest
from rest_framework.reverse import reverse
from rest_framework import status

from testutils.factories import ResourceFactory


class TestActiveResourcesList:
    @staticmethod
    def url():
        return reverse('core-api:api-resources-active')

    def test_admin_can_request_active_resources(self, admin_user, api_client):
        active_resource = ResourceFactory(active=True)
        _inactive_resource = ResourceFactory(active=False)

        response = api_client(user=admin_user).get(self.url())
        assert response.status_code == status.HTTP_200_OK

        resource_ids = [item.get('id') for item in response.json()]
        assert resource_ids == [active_resource.id]

    @pytest.mark.parametrize(
        ('permissions', 'expected_status_code'),
        (
            pytest.param([], status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param(
                ['manage_any_project'], status.HTTP_403_FORBIDDEN, id='project_manager_without_timesheet_perms'
            ),
            pytest.param(
                ['manage_any_timesheet'], status.HTTP_403_FORBIDDEN, id='timesheet_manager_without_project_perms'
            ),
            pytest.param(['view_any_project'], status.HTTP_403_FORBIDDEN, id='project_viewer_without_timesheet_perms'),
            pytest.param(
                ['view_any_timesheet'], status.HTTP_403_FORBIDDEN, id='timesheet_viewer_without_project_perms'
            ),
            pytest.param(
                ['view_any_project', 'view_any_timesheet'], status.HTTP_200_OK, id='project_viewer_and_timesheet_viewer'
            ),
            pytest.param(
                ['view_any_project', 'manage_any_timesheet'],
                status.HTTP_200_OK,
                id='project_viewer_and_timesheet_manager',
            ),
            pytest.param(
                ['manage_any_project', 'view_any_timesheet'],
                status.HTTP_200_OK,
                id='project_manager_and_timesheet_viewer',
            ),
            pytest.param(
                ['manage_any_project', 'manage_any_timesheet'],
                status.HTTP_200_OK,
                id='project_manager_and_timesheet_manager',
            ),
        ),
    )
    def test_regular_user_can_request_active_resources_only_if_authorized(
        self, permissions, expected_status_code, regular_user, api_client
    ):
        active_resource = ResourceFactory(active=True)
        _inactive_resource = ResourceFactory(active=False)

        for permission in permissions:
            regular_user.user_permissions.add(Permission.objects.get(codename=permission))

        response = api_client(user=regular_user).get(self.url())
        assert response.status_code == expected_status_code

        if expected_status_code < 400:
            resource_ids = [item.get('id') for item in response.json()]
            assert resource_ids == [active_resource.id]
