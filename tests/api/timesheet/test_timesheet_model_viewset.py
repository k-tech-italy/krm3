import typing
from datetime import date

import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from testutils.factories import (
    ContractFactory,
    GroupFactory,
    ResourceFactory,
    TimesheetSubmissionFactory,
    UserFactory,
)
from testutils.permissions import add_group_permissions, add_permissions

from krm3.core.models import TimesheetSubmission

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
            pytest.param('manager', 'full', id='manager'),
            pytest.param('group-manager', 'full', id='group-manager'),
            pytest.param('admin', 'full', id='admin'),
        ],
    )
    def test_write(  # noqa: PLR0917
        self, who, result, api_client, regular_user, manager, admin_user, group_manager
    ):
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
        ('who', 'method'),
        [
            pytest.param('regular', 'put', id='regular-put'),
            pytest.param('regular', 'patch', id='regular-patch'),
            pytest.param('regular', 'delete', id='regular-delete'),
            pytest.param('viewer', 'put', id='viewer-put'),
            pytest.param('viewer', 'patch', id='viewer-patch'),
            pytest.param('viewer', 'delete', id='viewer-delete'),
        ],
    )
    def test_unprivileged_users_cannot_modify_submission(
        self, who, method, api_client, regular_user, viewer
    ):
        user = regular_user if who == 'regular' else viewer
        resource = ResourceFactory(user=user)
        submission = TimesheetSubmissionFactory(resource=resource, closed=True)
        client = api_client(user=user)

        if method == 'delete':
            response = client.delete(self.url(submission.pk))
        else:
            response = getattr(client, method)(
                self.url(submission.pk),
                data={'closed': False},
                format='json',
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        submission.refresh_from_db()
        assert submission.closed is True

    def test_manager_can_reopen_submission(self, api_client, manager):
        submission = TimesheetSubmissionFactory(closed=True)

        response = api_client(user=manager).patch(
            self.url(submission.pk),
            data={'closed': False},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        submission.refresh_from_db()
        assert submission.closed is False

    @pytest.mark.parametrize(
        'method',
        [pytest.param('patch', id='reopen'), pytest.param('delete', id='delete')],
    )
    def test_manager_cannot_change_submission_before_a_later_closed_one(self, method, api_client, manager):
        resource = ResourceFactory()
        september = TimesheetSubmissionFactory(
            resource=resource,
            period=('2026-09-01', '2026-10-01'),
            closed=True,
        )
        TimesheetSubmissionFactory(
            resource=resource,
            period=('2026-10-01', '2026-11-01'),
            closed=True,
        )
        client = api_client(user=manager)

        if method == 'delete':
            response = client.delete(self.url(september.pk))
        else:
            response = client.patch(self.url(september.pk), data={'closed': False}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        september.refresh_from_db()
        assert september.closed is True

    def test_cannot_submit_after_a_missing_contracted_month(self, api_client, manager):
        resource = ResourceFactory()
        ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 4, 1)))
        TimesheetSubmissionFactory(
            resource=resource,
            period=('2026-01-01', '2026-02-01'),
            closed=True,
        )

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2026-03-01', '2026-03-31')},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'__all__': ['The timesheet for 2026-02 must be submitted first.']}

    @pytest.mark.parametrize(
        'who',
        [pytest.param('regular', id='regular'), pytest.param('viewer', id='viewer')],
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
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthorised_create_does_not_delete_other_users_open_submission(
        self, api_client, regular_user
    ):
        ResourceFactory(user=regular_user)
        victim_resource = ResourceFactory()
        existing_submission = TimesheetSubmissionFactory(
            resource=victim_resource,
            period=('2024-01-01', '2024-01-08'),
            closed=False,
        )

        response = api_client(user=regular_user).post(
            self.url(),
            data={
                'resource': victim_resource.pk,
                'period': ('2024-01-01', '2024-01-07'),
            },
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert TimesheetSubmission.objects.filter(pk=existing_submission.pk).exists()

    def test_invalid_resubmission_does_not_delete_existing_open_submission(
        self, api_client, regular_user
    ):
        resource = ResourceFactory(user=regular_user)
        existing_submission = TimesheetSubmissionFactory(
            resource=resource,
            period=('2024-01-01', '2024-01-08'),
            closed=False,
        )

        response = api_client(user=regular_user).post(
            self.url(),
            data={
                'resource': resource.pk,
                'period': ('2024-01-01', '2024-01-07'),
                'closed': 'invalid-value',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert TimesheetSubmission.objects.filter(pk=existing_submission.pk).exists()

    @pytest.mark.parametrize(
        'who, result',
        [
            pytest.param('regular', 'own', id='regular'),
            pytest.param('manager', 'full', id='manager'),
            pytest.param('group-manager', 'full', id='group-manager'),
            pytest.param('admin', 'full', id='admin'),
            pytest.param('viewer', 'full', id='viewer'),
        ],
    )
    def test_retrieve(  # noqa: PLR0917
        self, who, result, api_client, regular_user, manager, admin_user, group_manager, viewer
    ):
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
        expected = {own_ts.id} if result == 'own' else {own_ts.id, other_ts.id}

        response = api_client(user=user).get(self.url())
        assert response.status_code == status.HTTP_200_OK
        assert {r['id'] for r in response.data['results']} == expected

    def test_integrity_error_on_timesheet_creation(self, api_client, regular_user):
        resource: Resource = ResourceFactory(user=regular_user)
        # create and existing TimesheetSubmission with the same resource and overlapping period
        TimesheetSubmissionFactory(resource=resource, period=('2024-01-01', '2024-01-07'))
        response = api_client(user=regular_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-06', '2024-01-15')}, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            'error': 'conflicting key value violates exclusion constraint "exclude_overlapping_timesheets"\n'
            f'DETAIL:  Key (period, resource_id)=([2024-01-06,2024-01-16), {resource.pk})'
            f' conflicts with existing key (period, resource_id)=([2024-01-01,2024-01-07), {resource.pk}).'
        }

    def test_resubmit_open_timesheet(self, api_client, regular_user):
        resource: Resource = ResourceFactory(user=regular_user)
        # create and existing TimesheetSubmission with the same resource and overlapping period
        ts: TimesheetSubmission = TimesheetSubmissionFactory(
            resource=resource, period=('2024-01-01', '2024-01-08'), closed=False
        )
        assert ts.timesheet is None
        response = api_client(user=regular_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        ts = TimesheetSubmission.objects.get(pk=response.data['id'])
        assert ts.timesheet is not None
