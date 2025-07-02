import typing

import pytest

from testutils.factories import (
    ResourceFactory,
    UserFactory,
    TimesheetSubmissionFactory, GroupFactory,
)
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TimesheetSubmission
from testutils.permissions import add_permissions, add_group_permissions

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource


@pytest.fixture
def manager():
    manager = UserFactory()
    add_permissions(manager, 'core.manage_any_timesheet')
    return manager


@pytest.fixture
def viewer():
    viewer = UserFactory()
    add_permissions(viewer, 'core.view_any_timesheet')
    return viewer


@pytest.fixture
def group_manager():
    role = GroupFactory(name='manager')
    user = UserFactory()
    user.groups.add(role)
    add_group_permissions(role, 'core.manage_any_timesheet')
    return user


class TestTimesheetSubmissionModelAPIListView:
    @staticmethod
    def url(*args):
        if args:
            return reverse('core-api:api-timesheet-model-detail', args=args)
        return reverse('core-api:api-timesheet-model-list')

    @pytest.mark.parametrize(
        'who, result',
        [
            pytest.param('regular', 'own', id='regular'),
            pytest.param('manager', 'full', id='manager'),
            pytest.param('group-manager', 'full', id='group-manager'),
            pytest.param('admin', 'full', id='admin'),
        ],
    )
    def test_write(self, who, result, api_client, regular_user, manager, admin_user, group_manager):
        match who:
            case 'manager':
                user = manager
            case 'admin':
                user = admin_user
            case 'regular':
                user = regular_user
            case 'group-manager':
                user = group_manager

        resource: Resource = ResourceFactory(user=regular_user)
        response = api_client(user=user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        obj_id = response.data['id']
        assert response.status_code == status.HTTP_201_CREATED
        assert list(TimesheetSubmission.objects.values_list('id', flat=True)) == [obj_id]

        response = api_client(user=user).put(
            self.url(obj_id), data={'resource': resource.pk, 'period': ('2024-01-08', '2024-01-14')}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert TimesheetSubmission.objects.count() == 1

        response = api_client(user=user).delete(self.url(obj_id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert TimesheetSubmission.objects.count() == 0


    @pytest.mark.parametrize(
        'who',
        [
            pytest.param('regular', id='regular'),
            pytest.param('viewer', id='viewer')
        ],
    )
    def test_unauthorised_other(self, who, api_client, regular_user, viewer):
        match who:
            case 'regular':
                user = regular_user
            case 'viewer':
                user = viewer

        resource: Resource = ResourceFactory()

        response = api_client(user=user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        timesheet: TimesheetSubmission = TimesheetSubmissionFactory()
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
            pytest.param('group-manager', 'full', id='group-manager'),
            pytest.param('admin', 'full', id='admin'),
            pytest.param('viewer', 'full', id='viewer')
        ],
    )
    def test_retrieve(self, who, result, api_client, regular_user, manager, admin_user, group_manager, viewer):
        match who:
            case 'manager':
                user = manager
            case 'admin':
                user = admin_user
            case 'regular':
                user = regular_user
            case 'group-manager':
                user = group_manager
            case 'viewer':
                user = viewer

        resource: Resource = ResourceFactory(user=regular_user)
        own_ts = TimesheetSubmissionFactory(resource=resource)
        other_ts = TimesheetSubmissionFactory()
        expected = [own_ts.id] if result == 'own' else [own_ts.id, other_ts.id]

        response = api_client(user=user).get(self.url())
        assert response.status_code == status.HTTP_200_OK
        assert [r['id'] for r in response.data['results']] == expected

    def test_itegrity_error_on_timesheet_creation(self, api_client, regular_user):
        resource: Resource = ResourceFactory(user=regular_user)
        # create and existing TimesheetSubmission with the same resource and overlapping period
        TimesheetSubmissionFactory(resource=resource, period=('2024-01-01', '2024-01-07'))
        response = api_client(user=regular_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-06', '2024-01-15')}, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            'error': 'conflicting key value violates exclusion constraint "exclude_overlapping_timesheets"\n'
            f'DETAIL:  Key (period, resource_id)=([2024-01-06,2024-01-15), {resource.pk})'
            f' conflicts with existing key (period, resource_id)=([2024-01-01,2024-01-07), {resource.pk}).'
        }
