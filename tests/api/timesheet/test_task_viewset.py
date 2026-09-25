import datetime
import json
import typing
from decimal import Decimal

import pytest
from constance.test import override_config
from django.contrib.auth.models import Permission
from djangorestframework_camel_case.util import camelize
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ExtraHolidayFactory,
    ProjectFactory,
    ResourceFactory,
    TaskFactory,
    TaskEntryFactory,
    TimesheetSubmissionFactory,
)
from krm3.timesheet.api.serializers import DayEntryReadSerializer, TaskEntryReadSerializer

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Task

class TestTaskAPIListView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-timesheet-list')

    def test_returns_submission_state_for_requested_period(self, admin_user, api_client):
        resource = ResourceFactory()
        TimesheetSubmissionFactory(
            resource=resource,
            period=('2024-01-01', '2024-01-08'),
            closed=True,
        )

        response = api_client(user=admin_user).get(
            self.url(),
            data={'resource_id': resource.pk, 'start_date': '2024-01-01', 'end_date': '2024-01-07'},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['submitted'] is True

    @override_config(LESS_THAN_SCHEDULE_COLOR_BRIGHT_THEME='111111')
    @override_config(EXACT_SCHEDULE_COLOR_BRIGHT_THEME='222222')
    @override_config(MORE_THAN_SCHEDULE_COLOR_BRIGHT_THEME='333333')
    @override_config(LESS_THAN_SCHEDULE_COLOR_DARK_THEME='444444')
    @override_config(EXACT_SCHEDULE_COLOR_DARK_THEME='555555')
    @override_config(MORE_THAN_SCHEDULE_COLOR_DARK_THEME='666666')
    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 2})
    )
    @pytest.mark.parametrize(
        'task_end_date',
        (pytest.param(_dt('2024-12-31'), id='known_end'), pytest.param(None, id='open_ended')),
    )
    def test_returns_valid_timesheet_data(
        self,
        task_end_date,
        timesheet_api_user,
        api_client,
        timesheet_api_staff_user,
    ):
        project = ProjectFactory(period=(_dt('2022-01-01'), None))
        task_start_date = _dt('2023-01-01')
        period_start = _dt('2024-01-01')
        period_end = _dt('2024-01-07')

        resource: Resource = ResourceFactory()
        ContractFactory(resource=resource, period=(_dt('2020-01-01'), None))
        task: 'Task' = TaskFactory(
            resource=resource,
            project=project,
            period=(
                task_start_date,
                task_end_date + datetime.timedelta(days=1) if task_end_date else None,
            ),
        )

        TaskEntryFactory(task=task, resource=resource, date=_dt('2023-07-01'), comment='Too early')
        TaskEntryFactory(task=task, resource=resource, date=_dt('2024-07-01'), comment='Too late')

        entry_date = _dt('2024-01-03')
        day_entry = DayEntryFactory(
            resource=resource,
            day=entry_date,
            leave_hours=2,
            comment='Within range (day)',
        )
        task_entry = TaskEntryFactory(
            task=task,
            day_entry=day_entry,
            day_shift_hours=1,
            comment='Within range',
        )

        TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(_dt('2024-01-03'), _dt('2024-01-05')),
        )
        TimesheetSubmissionFactory(
            resource=resource,
            closed=False,
            period=(_dt('2024-01-05'), _dt('2024-01-07')),
        )

        api_data = {
            'resource_id': resource.pk,
            'start_date': period_start.isoformat(),
            'end_date': period_end.isoformat(),
        }
        response = api_client(user=timesheet_api_user).get(self.url(), data=api_data)

        assert response.status_code == status.HTTP_200_OK

        day_entry.refresh_from_db()
        task_entry.refresh_from_db()

        def _as_quantized_decimal(number: int | float | Decimal) -> str:
            return str(Decimal(number).quantize(Decimal('1.00')))

        expected_response = {
            'submitted': False,
            'tasks': [
                {
                    'id': task.pk,
                    'title': task.title,
                    'basket': task.basket_id,
                    'color': task.color,
                    'period': json.dumps({
                        'bounds': '[)',
                        'lower': task_start_date.isoformat(),
                        'upper': (
                            (task_end_date + datetime.timedelta(days=1)).isoformat() if task_end_date else None
                        ),
                    }),
                    'projectName': task.project.name,
                    'clientName': task.project.client.name,
                    'adminUrl': '',
                }
            ],
            'days': [
                (period_start + datetime.timedelta(days=offset)).isoformat()
                for offset in range((period_end - period_start).days + 1)
            ],
            'schedule': {
                '2024-01-01': 0,
                '2024-01-02': 2,
                '2024-01-03': 3,
                '2024-01-04': 4,
                '2024-01-05': 5,
                '2024-01-06': 0,
                '2024-01-07': 2,
            },
            'bankHours': _as_quantized_decimal(resource.get_bank_hours_balance(period_end)),
            'timesheetColors': {
                'lessThanScheduleColorBrightTheme': '111111',
                'exactScheduleColorBrightTheme': '222222',
                'moreThanScheduleColorBrightTheme': '333333',
                'lessThanScheduleColorDarkTheme': '444444',
                'exactScheduleColorDarkTheme': '555555',
                'moreThanScheduleColorDarkTheme': '666666',
            },
            'dayEntries': camelize(DayEntryReadSerializer([day_entry], many=True).data),
            'taskEntries': camelize(TaskEntryReadSerializer([task_entry], many=True).data),
        }

        assert response.json() == expected_response

        expected_response['tasks'][0]['adminUrl'] = reverse('admin:core_task_change', args=[task.pk])

        assert (
            api_client(user=timesheet_api_staff_user).get(self.url(), data=api_data).json() == expected_response
        ), 'check that for the task, a staff user receives a URL'
    def test_schedule_with_contract(self, admin_user, api_client):
        start_date = _dt('2020-05-01')
        end_date = _dt('2020-05-09')
        contract = ContractFactory(
            base_in__country__name='Poland',
            base_in__country__country_calendar_code='PL',
            base_in__subdivision_code=None,
            period=(start_date, end_date + datetime.timedelta(days=1)),
            working_schedule={
                'mon': 3,
                'tue': 4,
                'wed': 5,
                'thu': 6,
                'fri': 7,
                'sat': 8,
                'sun': 2,
            },
        )
        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': contract.resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert response.json()['schedule'] == {
            '2020-05-01': 0,
            '2020-05-02': 8,
            '2020-05-03': 0,
            '2020-05-04': 3,
            '2020-05-05': 4,
            '2020-05-06': 5,
            '2020-05-07': 6,
            '2020-05-08': 7,
            '2020-05-09': 8,
        }

    def test_schedule_with_multiple_contracts(self, admin_user, api_client):
        start_date = _dt('2020-05-01')
        end_date = _dt('2020-05-09')
        contract_1 = ContractFactory(
            base_in__country__name='Poland',
            base_in__country__country_calendar_code='PL',
            base_in__subdivision_code=None,
            period=(_dt('2020-05-01'), _dt('2020-05-04')),
            working_schedule={
                'mon': 2,
                'tue': 2,
                'wed': 2,
                'thu': 2,
                'fri': 2,
                'sat': 2,
                'sun': 2,
            },
        )
        ContractFactory(
            base_in__country__name='Poland',
            base_in__country__country_calendar_code='PL',
            base_in__subdivision_code=None,
            period=(_dt('2020-05-04'), _dt('2020-05-10')),
            resource=contract_1.resource,
            working_schedule={
                'mon': 4,
                'tue': 4,
                'wed': 4,
                'thu': 4,
                'fri': 4,
                'sat': 4,
                'sun': 4,
            },
        )
        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': contract_1.resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert response.json()['schedule'] == {
            '2020-05-01': 0,
            '2020-05-02': 2,
            '2020-05-03': 0,
            '2020-05-04': 4,
            '2020-05-05': 4,
            '2020-05-06': 4,
            '2020-05-07': 4,
            '2020-05-08': 4,
            '2020-05-09': 4,
        }

    @pytest.mark.parametrize(
        'extra_holiday_dates, expected_schedule',
        [
            (
                [{'start_date': _dt('2020-05-02'), 'end_date': _dt('2020-05-03')}],
                {
                    '2020-05-01': 0,
                    '2020-05-02': 0,
                    '2020-05-03': 0,
                    '2020-05-04': 3,
                    '2020-05-05': 4,
                    '2020-05-06': 5,
                    '2020-05-07': 6,
                    '2020-05-08': 7,
                    '2020-05-09': 8,
                    '2020-05-10': 2,
                },
            ),
            (
                [{'start_date': _dt('2020-05-08'), 'end_date': _dt('2020-05-10')}],
                {
                    '2020-05-01': 0,
                    '2020-05-02': 8,
                    '2020-05-03': 0,
                    '2020-05-04': 3,
                    '2020-05-05': 4,
                    '2020-05-06': 5,
                    '2020-05-07': 6,
                    '2020-05-08': 0,
                    '2020-05-09': 0,
                    '2020-05-10': 0,
                },
            ),
            (
                [
                    {'start_date': _dt('2020-05-01'), 'end_date': _dt('2020-05-01')},
                    {'start_date': _dt('2020-05-05'), 'end_date': _dt('2020-05-06')},
                ],
                {
                    '2020-05-01': 0,
                    '2020-05-02': 8,
                    '2020-05-03': 0,
                    '2020-05-04': 3,
                    '2020-05-05': 0,
                    '2020-05-06': 0,
                    '2020-05-07': 6,
                    '2020-05-08': 7,
                    '2020-05-09': 8,
                    '2020-05-10': 2,
                },
            ),
        ],
    )
    def test_schedule_with_extra_holidays(self, admin_user, api_client, extra_holiday_dates, expected_schedule):
        for date in extra_holiday_dates:
            ExtraHolidayFactory(
                period=(date['start_date'], date['end_date'] + datetime.timedelta(days=1)), country_codes=['PL']
            )

        start_date = _dt('2020-05-01')
        end_date = _dt('2020-05-10')
        contract = ContractFactory(
            base_in__country__name='Poland',
            base_in__country__country_calendar_code='PL',
            base_in__subdivision_code=None,
            period=(start_date, end_date + datetime.timedelta(days=1)),
            working_schedule={
                'mon': 3,
                'tue': 4,
                'wed': 5,
                'thu': 6,
                'fri': 7,
                'sat': 8,
                'sun': 2,
            },
        )

        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': contract.resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert response.json()['schedule'] == expected_schedule

    def test_picks_only_ongoing_tasks(self, admin_user, api_client):
        project = ProjectFactory(period=(_dt('2022-01-01'), None))

        time_entry_start_date = _dt('2024-01-01')
        time_entry_end_date = _dt('2024-01-07')

        resource: 'Resource' = ResourceFactory()
        ContractFactory(resource=resource, period=(_dt('2022-01-01'), None))

        _expired_task = TaskFactory(
            resource=resource,
            project=project,
            period=(_dt('2022-01-01'), _dt('2024-01-01')),
        )
        # NOTE: tasks expiring within the given range are considered ongoing
        expiring_task = TaskFactory(
            resource=resource,
            period=(_dt('2023-01-01'), _dt('2024-01-04')),
            project=_expired_task.project,
        )
        ongoing_task = TaskFactory(
            resource=resource,
            period=(_dt('2023-01-01'), _dt('2025-01-01')),
            project=_expired_task.project,
        )
        # NOTE: tasks starting within the given range are considered ongoing
        starting_midweek_task = TaskFactory(
            resource=resource,
            period=(_dt('2024-01-04'), _dt('2026-01-01')),
            project=_expired_task.project,
        )
        _future_task = TaskFactory(
            resource=resource,
            period=(_dt('2032-01-01'), _dt('2034-01-01')),
            project=_expired_task.project,
        )
        open_ended_task = TaskFactory(
            resource=resource, period=(_dt('2022-01-01'), None), project=_expired_task.project
        )

        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': resource.pk,
                'start_date': time_entry_start_date.isoformat(),
                'end_date': time_entry_end_date.isoformat(),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        actual_task_ids = {task_data.get('id') for task_data in response.json().get('tasks')}
        assert actual_task_ids == {expiring_task.id, ongoing_task.id, starting_midweek_task.id, open_ended_task.id}

    def test_admin_can_see_all_tasks(self, admin_user, api_client):
        user_resource = ResourceFactory()
        other_user_resource = ResourceFactory()

        start_date = _dt('2024-01-01')
        end_date = _dt('2025-01-01')

        project = ProjectFactory(period=(start_date, end_date + datetime.timedelta(days=1)))
        ContractFactory(resource=user_resource, period=project.period)
        ContractFactory(resource=other_user_resource, period=project.period)

        task_period = (start_date, end_date + datetime.timedelta(days=1))
        user_task = TaskFactory(resource=user_resource, project=project, period=task_period)
        other_user_task = TaskFactory(
            resource=other_user_resource, project=project, period=task_period
        )

        client = api_client(user=admin_user)

        user_response = client.get(
            self.url(),
            data={
                'resource_id': user_resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert user_response.status_code == status.HTTP_200_OK
        assert user_response.json().get('tasks', [])[0].get('id') == user_task.id

        other_user_response = client.get(
            self.url(),
            data={
                'resource_id': other_user_resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert other_user_response.status_code == status.HTTP_200_OK
        assert other_user_response.json().get('tasks', [])[0].get('id') == other_user_task.id

    @pytest.mark.parametrize(
        ('permissions', 'expected_status_code'),
        [
            pytest.param([], status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param(
                ['manage_any_project'], status.HTTP_403_FORBIDDEN, id='project_manager_without_timesheet_perms'
            ),
            pytest.param(['view_any_project'], status.HTTP_403_FORBIDDEN, id='project_viewer_without_timesheet_perms'),
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
        ],
    )
    def test_regular_user_can_see_tasks_based_on_permissions(
        self, permissions, expected_status_code, regular_user, api_client
    ):
        user_resource = ResourceFactory(user=regular_user)
        other_user_resource = ResourceFactory()

        for permission in permissions:
            regular_user.user_permissions.add(Permission.objects.get(codename=permission))

        start_date = _dt('2024-01-01')
        end_date = _dt('2025-01-01')

        project = ProjectFactory(period=(start_date, end_date + datetime.timedelta(days=1)))
        ContractFactory(resource=user_resource, period=project.period)
        ContractFactory(resource=other_user_resource, period=project.period)
        task_period = (start_date, end_date + datetime.timedelta(days=1))
        user_task = TaskFactory(resource=user_resource, project=project, period=task_period)
        other_user_task = TaskFactory(
            resource=other_user_resource, project=project, period=task_period
        )

        client = api_client(user=regular_user)

        user_response = client.get(
            self.url(),
            data={
                'resource_id': user_resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert user_response.status_code == status.HTTP_200_OK
        assert user_response.json().get('tasks', [])[0].get('id') == user_task.id

        other_user_response = client.get(
            self.url(),
            data={
                'resource_id': other_user_resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert (status_code := other_user_response.status_code) == expected_status_code
        if status_code == status.HTTP_200_OK:
            assert other_user_response.json().get('tasks', [])[0].get('id') == other_user_task.id


import datetime

import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from testutils.factories import ResourceFactory


class TestTimesheetRequestValidation:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-timesheet-list')

    def test_rejects_unauthenticated_users(self, api_client):
        resource = ResourceFactory()
        response = api_client().get(
            self.url(), data={'resource_id': resource.pk, 'start_date': '2024-01-01', 'end_date': '2024-01-07'}
        )
        # SessionAuthentication returns 403 Forbidden (CSRF check) instead of 401
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_missing_query_params(self, admin_user, api_client):
        client = api_client(user=admin_user)
        params = {}
        expected_error_payload = {'error': 'Required query parameter(s) missing.'}

        response = client.get(self.url(), data=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == expected_error_payload

        resource = ResourceFactory()
        params.setdefault('resource_id', resource.pk)
        response = client.get(self.url(), data=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == expected_error_payload

        params.setdefault('start_date', '2024-01-01')
        response = client.get(self.url(), data=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == expected_error_payload

        params.setdefault('end_date', '2024-01-07')
        response = client.get(self.url(), data=params)
        assert response.status_code == status.HTTP_200_OK

    _iso_date_test_cases = [
        pytest.param('2024-01-01', status.HTTP_200_OK, id='ISO'),
        pytest.param('20240101', status.HTTP_200_OK, id='yyyymmdd'),
        pytest.param('2024/01/01', status.HTTP_400_BAD_REQUEST, id='yyyy/mm/dd'),
        pytest.param('2024-01', status.HTTP_400_BAD_REQUEST, id='year_month'),
        pytest.param('2024', status.HTTP_400_BAD_REQUEST, id='year'),
        pytest.param(datetime.datetime(2024, 1, 1), status.HTTP_400_BAD_REQUEST, id='timestamp'),
    ]

    @pytest.mark.parametrize(('start_date', 'expected_status_code'), _iso_date_test_cases)
    def test_rejects_non_iso_start_date(self, start_date, expected_status_code, admin_user, api_client):
        resource = ResourceFactory()
        params = {'resourceId': resource.pk, 'startDate': start_date, 'endDate': '2024-01-07'}
        response = api_client(user=admin_user).get(self.url(), data=params)
        assert response.status_code == expected_status_code
        if expected_status_code >= 400:
            assert response.data == {'error': 'Cannot parse start date.'}

    @pytest.mark.parametrize(('end_date', 'expected_status_code'), _iso_date_test_cases)
    def test_rejects_non_iso_end_date(self, end_date, expected_status_code, admin_user, api_client):
        resource = ResourceFactory()
        params = {'resource_id': resource.pk, 'start_date': '2023-12-26', 'end_date': end_date}
        response = api_client(user=admin_user).get(self.url(), data=params)
        assert response.status_code == expected_status_code
        if expected_status_code >= 400:
            assert response.data == {'error': 'Cannot parse end date.'}

    @pytest.mark.parametrize(
        ('end_date', 'expected_status_code'),
        [
            pytest.param('2023-12-26', status.HTTP_400_BAD_REQUEST, id='end_date_earlier_than_start_date'),
            pytest.param('2024-01-01', status.HTTP_200_OK, id='end_date_same_as_start_date'),
            pytest.param('2024-01-07', status.HTTP_200_OK, id='end_date_later_than_start_date'),
        ],
    )
    def test_validates_date_range(self, end_date, expected_status_code, admin_user, api_client):
        resource = ResourceFactory()
        params = {'resource_id': resource.pk, 'start_date': '2024-01-01', 'end_date': end_date}
        response = api_client(user=admin_user).get(self.url(), data=params)
        assert response.status_code == expected_status_code
        if expected_status_code >= 400:
            assert response.data == {'error': 'Start date must be earlier than end date.'}
