import typing
from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    GroupFactory,
    ResourceFactory,
    TimesheetSubmissionFactory,
    UserFactory,
    create_contract_without_scheduled_hours,
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

    def test_submission_without_contract_is_created(self, api_client, manager):
        resource = ResourceFactory()

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize(
        'data',
        [
            pytest.param({'period': ('2026-09-07', '2026-09-07')}, id='missing'),
            pytest.param(
                {'resource': 'not-a-resource', 'period': ('2026-09-07', '2026-09-07')},
                id='malformed',
            ),
        ],
    )
    def test_invalid_resource_returns_field_error(self, data, api_client, regular_user):
        ResourceFactory(user=regular_user)

        response = api_client(user=regular_user).post(self.url(), data=data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'resource' in response.data

    @pytest.mark.parametrize(
        'resource_id_type',
        [
            pytest.param('integer', id='integer'),
            pytest.param('numeric-string', id='numeric-string'),
        ],
    )
    def test_regular_user_can_create_submission_for_own_resource(self, resource_id_type, api_client, regular_user):
        resource = ResourceFactory(user=regular_user)
        resource_id = str(resource.pk) if resource_id_type == 'numeric-string' else resource.pk

        response = api_client(user=regular_user).post(
            self.url(),
            data={'resource': resource_id, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['resource'] == resource.pk

    def test_regular_user_cannot_create_submission_for_another_resource(self, api_client, regular_user):
        ResourceFactory(user=regular_user)
        other_resource = ResourceFactory()

        response = api_client(user=regular_user).post(
            self.url(),
            data={'resource': other_resource.pk, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_create_submission_for_any_resource(self, api_client, manager):
        resource = ResourceFactory()

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_api_exposes_readonly_status(self, api_client, manager):
        resource = ResourceFactory()
        client = api_client(user=manager)

        response = client.post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == TimesheetSubmission.Status.CLOSED
        assert 'closed' not in response.data
        submission = TimesheetSubmission.objects.get(pk=response.data['id'])
        assert submission.status == TimesheetSubmission.Status.CLOSED

        response = client.patch(
            self.url(submission.pk),
            data={'status': 'draft'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == TimesheetSubmission.Status.CLOSED
        assert 'closed' not in response.data
        submission.refresh_from_db()
        assert submission.status == TimesheetSubmission.Status.CLOSED

    def test_incomplete_submission_returns_bad_request(self, api_client, manager):
        contract = ContractFactory(
            period=(date(2026, 9, 7), date(2026, 9, 8)),
            working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
        )
        DayEntryFactory(
            resource=contract.resource,
            contract=contract,
            day=date(2026, 9, 7),
            day_hours=Decimal('6.00'),
            due_hours=Decimal('8.00'),
        )

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': contract.resource_id, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'__all__': ['The timesheet has incomplete scheduled days.']}

    def test_complete_submission_without_tasks_is_created(self, api_client, manager):
        contract = ContractFactory(
            period=(date(2026, 9, 7), date(2026, 9, 8)),
            working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
        )
        DayEntryFactory(
            resource=contract.resource,
            contract=contract,
            day=date(2026, 9, 7),
            day_hours=Decimal('8.00'),
            due_hours=Decimal('8.00'),
        )

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': contract.resource_id, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_submission_without_tasks_or_day_entries_returns_bad_request(self, api_client, manager):
        contract = ContractFactory(
            period=(date(2026, 9, 7), date(2026, 9, 8)),
            working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
        )

        response = api_client(user=manager).post(
            self.url(),
            data={'resource': contract.resource_id, 'period': ('2026-09-07', '2026-09-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'__all__': ['The timesheet has incomplete scheduled days.']}

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

    def test_owner_can_resubmit_rejected_submission(self, api_client, regular_user):
        resource = ResourceFactory(user=regular_user)
        rejected = TimesheetSubmissionFactory(
            resource=resource,
            period=('2024-01-01', '2024-01-08'),
            status=TimesheetSubmission.Status.REJECTED,
        )

        response = api_client(user=regular_user).post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == TimesheetSubmission.Status.CLOSED
        assert response.data['id'] != rejected.pk
        assert TimesheetSubmission.objects.filter(pk=rejected.pk).exists() is False
        assert TimesheetSubmission.objects.count() == 1

    @pytest.mark.parametrize(
        ('entries', 'period', 'expected_status'),
        [
            pytest.param(
                [(date(2026, 9, 30), Decimal('16.00'))],
                ('2026-09-30', '2026-09-30'),
                TimesheetSubmission.Status.CLOSED,
                id='within-limit',
            ),
            pytest.param(
                [(date(2026, 9, 29), Decimal('16.00')), (date(2026, 9, 30), Decimal('1.00'))],
                ('2026-09-29', '2026-09-30'),
                TimesheetSubmission.Status.PENDING,
                id='above-limit',
            ),
        ],
    )
    def test_submission_status_depends_on_final_bank_balance(
        self, entries, period, expected_status, api_client, regular_user
    ):
        resource = ResourceFactory(user=regular_user)
        contract = create_contract_without_scheduled_hours(resource, (date(2026, 9, 1), date(2026, 10, 1)))
        for day, bank in entries:
            DayEntryFactory(resource=resource, contract=contract, day=day, bank=bank, due_hours=0)

        response = api_client(user=regular_user).post(
            self.url(),
            data={'resource': resource.pk, 'period': period},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['status'] == expected_status

    @pytest.mark.parametrize(
        'blocking_status',
        [TimesheetSubmission.Status.PENDING, TimesheetSubmission.Status.REJECTED],
    )
    def test_pending_or_rejected_previous_submission_blocks_later_submission(
        self, blocking_status, api_client, regular_user
    ):
        resource = ResourceFactory(user=regular_user)
        TimesheetSubmissionFactory(
            resource=resource,
            period=('2026-09-01', '2026-10-01'),
            status=blocking_status,
        )

        response = api_client(user=regular_user).post(
            self.url(),
            data={'resource': resource.pk, 'period': ('2026-10-01', '2026-11-01')},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['__all__'] == ['A previous timesheet is still pending review or rejected.']

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
        submission = TimesheetSubmissionFactory(resource=resource, status=TimesheetSubmission.Status.CLOSED)
        client = api_client(user=user)

        if method == 'delete':
            response = client.delete(self.url(submission.pk))
        else:
            response = getattr(client, method)(
                self.url(submission.pk),
                data={'status': TimesheetSubmission.Status.DRAFT},
                format='json',
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        submission.refresh_from_db()
        assert submission.is_closed is True

    def test_cannot_submit_after_a_missing_contracted_month(self, api_client, manager):
        resource = ResourceFactory()
        ContractFactory(
            resource=resource,
            period=(date(2026, 1, 1), date(2026, 4, 1)),
            working_schedule={'mon': 0, 'tue': 0, 'wed': 0, 'thu': 0, 'fri': 0, 'sat': 0, 'sun': 0},
        )
        TimesheetSubmissionFactory(
            resource=resource,
            period=('2026-01-01', '2026-02-01'),
            status=TimesheetSubmission.Status.CLOSED,
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
            status=TimesheetSubmission.Status.DRAFT,
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
        self, api_client, manager
    ):
        resource = ResourceFactory()
        existing_submission = TimesheetSubmissionFactory(
            resource=resource,
            period=('2024-01-01', '2024-01-08'),
            status=TimesheetSubmission.Status.DRAFT,
        )

        response = api_client(user=manager).post(
            self.url(),
            data={
                'resource': resource.pk,
                'period': ('invalid', 'invalid'),
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
            resource=resource, period=('2024-01-01', '2024-01-08'), status=TimesheetSubmission.Status.DRAFT
        )
        assert ts.timesheet is None
        response = api_client(user=regular_user).post(
            self.url(), data={'resource': resource.pk, 'period': ('2024-01-01', '2024-01-07')}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        ts = TimesheetSubmission.objects.get(pk=response.data['id'])
        assert ts.timesheet is not None
