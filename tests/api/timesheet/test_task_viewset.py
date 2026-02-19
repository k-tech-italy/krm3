import json
import datetime
import logging
import typing
from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core import exceptions
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth.models import Permission
from django import test as django_test
from testutils.factories import (
    ContractFactory,
    ExtraHolidayFactory,
    ProjectFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TimeEntryFactory,
    TimesheetSubmissionFactory,
    UserFactory,
    TimesheetSubmissionFactory,
    ContractFactory,
    ExtraHolidayFactory,
)
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TimeEntry

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Task

# NOTE: special leaves are leave entries with a reason. They have their own tests.
_day_entry_kinds = ('sick', 'holiday', 'leave', 'rest')
_day_entry_keys = tuple(f'{key}Hours' for key in _day_entry_kinds)

_task_entry_kinds = ('day_shift', 'night_shift', 'travel')
_task_entry_keys = ('dayShiftHours', 'nightShiftHours', 'travelHours')

_computed_hours_kinds = (*_day_entry_kinds, *_task_entry_kinds)
_computed_hours_keys = (*_day_entry_keys, *_task_entry_keys)

_all_hours_kinds = (*_computed_hours_kinds, 'on_call')
_all_hours_keys = (*_computed_hours_keys, 'onCallHours')


class TestTaskAPIListView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-timesheet-list')

    def test_rejects_unauthenticated_users(self, api_client):
        resource: Resource = ResourceFactory()
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
        resource: 'Resource' = ResourceFactory()
        params = {'resourceId': resource.pk, 'startDate': start_date, 'endDate': '2024-01-07'}
        response = api_client(user=admin_user).get(self.url(), data=params)
        assert response.status_code == expected_status_code
        if expected_status_code >= 400:
            assert response.data == {'error': 'Cannot parse start date.'}

    @pytest.mark.parametrize(('end_date', 'expected_status_code'), _iso_date_test_cases)
    def test_rejects_non_iso_end_date(self, end_date, expected_status_code, admin_user, api_client):
        resource: Resource = ResourceFactory()
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
        resource: 'Resource' = ResourceFactory()
        params = {'resource_id': resource.pk, 'start_date': '2024-01-01', 'end_date': end_date}
        response = api_client(user=admin_user).get(self.url(), data=params)
        assert response.status_code == expected_status_code
        if expected_status_code >= 400:
            assert response.data == {'error': 'Start date must be earlier than end date.'}

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
        (pytest.param(datetime.date(2024, 12, 31), id='known_end'), pytest.param(None, id='open_ended')),
    )
    def test_returns_valid_time_entry_data(
        self,
        task_end_date,
        timesheet_api_user,
        api_client,
        timesheet_api_staff_user,
    ):
        project = ProjectFactory(start_date=datetime.date(2022, 1, 1))

        task_start_date = datetime.date(2023, 1, 1)

        time_entry_start_date = datetime.date(2024, 1, 1)
        time_entry_end_date = datetime.date(2024, 1, 7)

        resource: Resource = ResourceFactory()
        task: 'Task' = TaskFactory(
            resource=resource, project=project, start_date=task_start_date, end_date=task_end_date
        )

        def _make_time_entry(**kwargs):
            return TimeEntryFactory(task=kwargs.pop('task', task), resource=resource, **kwargs)

        date_within_range = datetime.date(2024, 1, 3)

        _early_time_entry = _make_time_entry(date=datetime.date(2023, 7, 1), comment='Too early')
        _late_time_entry = _make_time_entry(date=datetime.date(2024, 7, 1), comment='Too late')
        task_entry_within_range = _make_time_entry(date=date_within_range, day_shift_hours=1, comment='Within range')
        day_entry_within_range = _make_time_entry(
            date=date_within_range, task=None, day_shift_hours=0, leave_hours=2, comment='Within range (day)'
        )
        # Timesheets are assigned to closed entry via 'link_entries' - Timesheet post-save signal
        TimesheetSubmissionFactory(
            resource=resource, closed=True, period=((datetime.date(2024, 1, 3), datetime.date(2024, 1, 5)))
        )
        TimesheetSubmissionFactory(
            resource=resource, closed=False, period=((datetime.date(2024, 1, 5), datetime.date(2024, 1, 7)))
        )

        api_data = {
            'resource_id': resource.pk,
            'start_date': time_entry_start_date.isoformat(),
            'end_date': time_entry_end_date.isoformat(),
        }
        response = api_client(user=timesheet_api_user).get(
            self.url(),
            data=api_data,
        )

        assert response.status_code == status.HTTP_200_OK

        def _as_quantized_decimal(n: int | float | Decimal) -> str:
            return str(Decimal(n).quantize(Decimal('1.00')))

        expected_response = {
            'tasks': [
                {
                    'id': task.pk,
                    'title': task.title,
                    'basketTitle': task.basket_title,
                    'color': task.color,
                    'startDate': task_start_date.isoformat(),
                    'endDate': task_end_date.isoformat() if task_end_date else None,
                    'projectName': task.project.name,
                    'clientName': task.project.client.name,
                    'adminUrl': '',
                }
            ],
            'timeEntries': [
                {
                    'id': task_entry_within_range.id,
                    'date': date_within_range.isoformat(),
                    'lastModified': task_entry_within_range.last_modified.isoformat(),
                    'dayShiftHours': _as_quantized_decimal(task_entry_within_range.day_shift_hours),
                    'sickHours': _as_quantized_decimal(task_entry_within_range.sick_hours),
                    'holidayHours': _as_quantized_decimal(task_entry_within_range.holiday_hours),
                    'leaveHours': _as_quantized_decimal(task_entry_within_range.leave_hours),
                    'specialLeaveHours': _as_quantized_decimal(task_entry_within_range.leave_hours),
                    'specialLeaveReason': task_entry_within_range.special_leave_reason,
                    'nightShiftHours': _as_quantized_decimal(task_entry_within_range.night_shift_hours),
                    'onCallHours': _as_quantized_decimal(task_entry_within_range.on_call_hours),
                    'travelHours': _as_quantized_decimal(task_entry_within_range.travel_hours),
                    'restHours': _as_quantized_decimal(task_entry_within_range.rest_hours),
                    'bankFrom': _as_quantized_decimal(task_entry_within_range.bank_from),
                    'bankTo': _as_quantized_decimal(day_entry_within_range.bank_to),
                    'comment': 'Within range',
                    'protocolNumber': None,
                    'task': task.pk,
                    'taskTitle': task.title,
                },
                {
                    'id': day_entry_within_range.id,
                    'date': date_within_range.isoformat(),
                    'lastModified': day_entry_within_range.last_modified.isoformat(),
                    'dayShiftHours': _as_quantized_decimal(day_entry_within_range.day_shift_hours),
                    'sickHours': _as_quantized_decimal(day_entry_within_range.sick_hours),
                    'holidayHours': _as_quantized_decimal(day_entry_within_range.holiday_hours),
                    'leaveHours': _as_quantized_decimal(day_entry_within_range.leave_hours),
                    'specialLeaveHours': _as_quantized_decimal(day_entry_within_range.special_leave_hours),
                    'specialLeaveReason': day_entry_within_range.special_leave_reason,
                    'nightShiftHours': _as_quantized_decimal(day_entry_within_range.night_shift_hours),
                    'onCallHours': _as_quantized_decimal(day_entry_within_range.on_call_hours),
                    'travelHours': _as_quantized_decimal(day_entry_within_range.travel_hours),
                    'restHours': _as_quantized_decimal(day_entry_within_range.rest_hours),
                    'bankFrom': _as_quantized_decimal(day_entry_within_range.bank_from),
                    'bankTo': _as_quantized_decimal(day_entry_within_range.bank_to),
                    'comment': 'Within range (day)',
                    'protocolNumber': None,
                    'task': None,
                    'taskTitle': None,
                },
            ],
            'days': {
                '2024-01-01': {
                    'hol': True,
                    'nwd': True,
                    'closed': False,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-02': {
                    'hol': False,
                    'nwd': False,
                    'closed': False,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-03': {
                    'hol': False,
                    'nwd': False,
                    'closed': True,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 1.0,
                    'holidayHours': 0.0,
                    'leaveHours': 2.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-04': {
                    'hol': False,
                    'nwd': False,
                    'closed': True,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-05': {
                    'hol': False,
                    'nwd': False,
                    'closed': False,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-06': {
                    'hol': True,
                    'nwd': True,
                    'closed': False,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
                '2024-01-07': {
                    'hol': True,
                    'nwd': True,
                    'closed': False,
                    'mealVoucher': None,
                    'bankFrom': 0.0,
                    'bankTo': 0.0,
                    'dayShiftHours': 0.0,
                    'holidayHours': 0.0,
                    'leaveHours': 0.0,
                    'nightShiftHours': 0.0,
                    'onCallHours': 0.0,
                    'overtime': 0.0,
                    'restHours': 0.0,
                    'sickHours': 0.0,
                    'specialLeaveHours': 0.0,
                    'specialLeaveReason': None,
                    'travelHours': 0.0,
                },
            },
            'schedule': {
                '2024-01-01': 0,
                '2024-01-02': 2,
                '2024-01-03': 3,
                '2024-01-04': 4,
                '2024-01-05': 5,
                '2024-01-06': 0,
                '2024-01-07': 2,
            },
            'bankHours': _as_quantized_decimal(resource.get_bank_hours_balance()),
            'timesheetColors': {
                'lessThanScheduleColorBrightTheme': '111111',
                'exactScheduleColorBrightTheme': '222222',
                'moreThanScheduleColorBrightTheme': '333333',
                'lessThanScheduleColorDarkTheme': '444444',
                'exactScheduleColorDarkTheme': '555555',
                'moreThanScheduleColorDarkTheme': '666666',
            },
        }

        assert response.json() == expected_response

        expected_response['tasks'][0]['adminUrl'] = reverse('admin:core_task_change', args=[task.pk])

        assert (
            api_client(user=timesheet_api_staff_user)
            .get(
                self.url(),
                data=api_data,
            )
            .json()
            == expected_response
        ), 'check that for the task, a staff user receives a URL'

    def test_schedule_with_contract(self, admin_user, api_client):
        start_date = datetime.date(2020, 5, 1)
        end_date = datetime.date(2020, 5, 9)
        contract = ContractFactory(
            country_calendar_code='PL',
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
        start_date = datetime.date(2020, 5, 1)
        end_date = datetime.date(2020, 5, 9)
        contract_1 = ContractFactory(
            country_calendar_code='PL',
            period=(datetime.date(2020, 5, 1), datetime.date(2020, 5, 4)),
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
            country_calendar_code='PL',
            period=(datetime.date(2020, 5, 4), datetime.date(2020, 5, 10)),
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
                [{'start_date': datetime.date(2020, 5, 2), 'end_date': datetime.date(2020, 5, 3)}],
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
                [{'start_date': datetime.date(2020, 5, 8), 'end_date': datetime.date(2020, 5, 10)}],
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
                    {'start_date': datetime.date(2020, 5, 1), 'end_date': datetime.date(2020, 5, 1)},
                    {'start_date': datetime.date(2020, 5, 5), 'end_date': datetime.date(2020, 5, 6)},
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

        start_date = datetime.date(2020, 5, 1)
        end_date = datetime.date(2020, 5, 10)
        contract = ContractFactory(
            country_calendar_code='PL',
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
        project = ProjectFactory(start_date=datetime.date(2022, 1, 1))

        time_entry_start_date = datetime.date(2024, 1, 1)
        time_entry_end_date = datetime.date(2024, 1, 7)

        resource: 'Resource' = ResourceFactory()

        _expired_task = TaskFactory(
            resource=resource,
            project=project,
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )
        # NOTE: tasks expiring within the given range are considered ongoing
        expiring_task = TaskFactory(
            resource=resource,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2024, 1, 3),
            project=_expired_task.project,
        )
        ongoing_task = TaskFactory(
            resource=resource,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            project=_expired_task.project,
        )
        # NOTE: tasks starting within the given range are considered ongoing
        starting_midweek_task = TaskFactory(
            resource=resource,
            start_date=datetime.date(2024, 1, 4),
            end_date=datetime.date(2025, 12, 31),
            project=_expired_task.project,
        )
        _future_task = TaskFactory(
            resource=resource,
            start_date=datetime.date(2032, 1, 1),
            end_date=datetime.date(2033, 12, 31),
            project=_expired_task.project,
        )
        open_ended_task = TaskFactory(
            resource=resource, start_date=datetime.date(2022, 1, 1), end_date=None, project=_expired_task.project
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

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2025, 1, 1)

        project = ProjectFactory(start_date=start_date)

        user_task = TaskFactory(resource=user_resource, project=project, start_date=start_date, end_date=end_date)
        other_user_task = TaskFactory(
            resource=other_user_resource, project=project, start_date=start_date, end_date=end_date
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

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2025, 1, 1)

        project = ProjectFactory(start_date=start_date)
        user_task = TaskFactory(resource=user_resource, project=project, start_date=start_date, end_date=end_date)
        other_user_task = TaskFactory(
            resource=other_user_resource, project=project, start_date=start_date, end_date=end_date
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
        if status_code <= 400:
            assert other_user_response.json().get('tasks', [])[0].get('id') == other_user_task.id


class TestTimeEntryAPICreateView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-time-entry-list')

    @pytest.mark.parametrize(
        ('day_shift_hours', 'optional_data'),
        (
            pytest.param(0, {}, id='no_work'),
            pytest.param(8, {}, id='only_day_shift_hours'),
            pytest.param(
                1,
                {'nightShiftHours': 1, 'onCallHours': 1, 'travelHours': 0.5},
                id='task_entry_with_optional_hours',
            ),
        ),
    )
    def test_creates_single_valid_task_entry(self, day_shift_hours, optional_data, admin_user, api_client):
        task = TaskFactory()
        assert not TimeEntry.objects.filter(task=task).exists()

        time_entry_data = {
            'dates': ['2024-01-01'],
            'dayShiftHours': day_shift_hours,
            'taskId': task.pk,
            'resourceId': task.resource.pk,
        } | optional_data

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(task=task).exists()

    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
    )
    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'leaveHours': 2}, id='day_entry_leave'),
            pytest.param({'holidayHours': 8}, id='day_entry_holiday'),
            pytest.param({'sickHours': 8}, id='day_entry_sick'),
        ),
    )
    def test_creates_single_valid_day_entry(self, hours_data, admin_user, api_client):
        resource = ResourceFactory()
        time_entry_data = {
            'dates': ['2024-01-02'],
            'dayShiftHours': 0,
            'resourceId': resource.pk,
            'comment': 'approved',
        } | hours_data

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        entries = TimeEntry.objects.filter(resource=resource)
        assert entries.exists()
        day_entry = entries.get()
        assert day_entry.special_leave_hours == 0
        assert day_entry.special_leave_reason is None

    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
    )
    def test_creates_single_valid_special_leave_entry(self, api_client, admin_user):
        resource = ResourceFactory()
        reason = SpecialLeaveReasonFactory()
        time_entry_data = {
            'dates': ['2024-01-02'],
            'dayShiftHours': 0,
            'specialLeaveHours': 8,
            'specialLeaveReason': reason.pk,
            'resourceId': resource.pk,
            'comment': 'approved',
        }
        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        entries = TimeEntry.objects.filter(resource=resource)
        assert entries.exists()
        special_leave = entries.get()
        assert special_leave.leave_hours == 0
        assert special_leave.special_leave_hours == 8
        assert special_leave.special_leave_reason == reason

    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
    )
    @pytest.mark.parametrize(
        ('dates', 'expected_status_code'),
        (
            pytest.param(['2024-01-02'], status.HTTP_201_CREATED, id='one_day_at_start'),
            pytest.param(['2024-01-15'], status.HTTP_201_CREATED, id='one_day_within_range'),
            pytest.param(['2024-01-31'], status.HTTP_201_CREATED, id='one_day_at_end'),
            pytest.param(['2023-12-31'], status.HTTP_400_BAD_REQUEST, id='one_day_before_start'),
            pytest.param(['2024-02-01'], status.HTTP_400_BAD_REQUEST, id='one_day_after_end'),
            pytest.param(['2023-12-30', '2023-12-31'], status.HTTP_400_BAD_REQUEST, id='range_before_start'),
            pytest.param(['2023-12-31', '2024-01-01'], status.HTTP_400_BAD_REQUEST, id='range_overlapping_start'),
            pytest.param(['2024-02-01', '2024-02-02'], status.HTTP_400_BAD_REQUEST, id='range_after_end'),
            pytest.param(['2024-01-31', '2024-02-01'], status.HTTP_400_BAD_REQUEST, id='range_overlapping_end'),
            pytest.param(
                ['2023-12-31', *[f'2024-01-{x:02d}' for x in range(1, 32)], '2024-02-01'],
                status.HTTP_400_BAD_REQUEST,
                id='range_containing_validity_period',
            ),
            pytest.param(
                [f'2024-01-{x:02d}' for x in range(11, 16)], status.HTTP_201_CREATED, id='range_within_validity_period'
            ),
            pytest.param(  # 2024-01-06 italian holiday
                [f'2024-01-{x:02d}' for x in range(2, 32) if x != 6],
                status.HTTP_201_CREATED,
                id='range_equal_to_validity_period',
            ),
        ),
    )
    def test_accepts_special_leave_only_if_reason_is_valid(self, dates, expected_status_code, api_client, admin_user):
        resource = ResourceFactory()
        reason = SpecialLeaveReasonFactory(from_date=datetime.date(2024, 1, 1), to_date=datetime.date(2024, 1, 31))
        time_entry_data = {
            'dates': dates,
            'dayShiftHours': 0,
            'specialLeaveHours': 8,
            'specialLeaveReason': reason.pk,
            'resourceId': resource.pk,
            'comment': 'approved',
        }
        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == expected_status_code
        assert TimeEntry.objects.exists() is (expected_status_code == status.HTTP_201_CREATED)

    @pytest.mark.parametrize(
        (
            'task_1_hours',
            'task_2_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'expected_autofill',
        ),
        (
            pytest.param(0, 0, 0, 0, 0, 8, id='empty_day'),
            pytest.param(3, 0, 0, 0, 0, 5, id='same_task_partial_fills_to_8'),
            pytest.param(0, 3, 0, 0, 0, 5, id='other_task_partial_fills_to_8'),
            pytest.param(2, 3, 0, 0, 0, 3, id='two_tasks_partial_fills_to_8'),
            pytest.param(0, 0, 8, 0, 0, 0, id='full_sick_leave'),
            pytest.param(0, 0, 0, 8, 0, 0, id='full_holiday'),
            pytest.param(10, 0, 0, 0, 0, 0, id='overtime_same_task_no_change'),
            pytest.param(0, 10, 0, 0, 0, 0, id='overtime_other_task_no_change'),
            pytest.param(0, 8, 0, 0, 0, 0, id='full_day_other_task_no_change'),
            pytest.param(2, 0, 0, 0, 2, 4, id='task_and_leave'),
            pytest.param(0, 0, 0, 0, 4, 4, id='leave_half_day'),
        ),
    )
    def test_autofill_scenarios(
        self,
        task_1_hours,
        task_2_hours,
        sick_hours,
        holiday_hours,
        leave_hours,
        expected_autofill,
        api_client,
        admin_user,
    ):
        resource = ResourceFactory()
        date_str = '2024-01-08'
        date_obj = datetime.date.fromisoformat(date_str)
        ContractFactory(
            resource=resource,
            period=(date_obj, None),
            working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
        )
        task_1 = TaskFactory(resource=resource, title='Task 1')
        task_2 = TaskFactory(resource=resource, title='Task 2')

        if task_1_hours > 0:
            TimeEntryFactory(resource=resource, date=date_obj, task=task_1, day_shift_hours=task_1_hours)
        if task_2_hours > 0:
            TimeEntryFactory(resource=resource, date=date_obj, task=task_2, day_shift_hours=task_2_hours)
        if sick_hours > 0:
            TimeEntryFactory(resource=resource, date=date_obj, task=None, sick_hours=sick_hours, day_shift_hours=0)
        if holiday_hours > 0:
            TimeEntryFactory(
                resource=resource, date=date_obj, task=None, holiday_hours=holiday_hours, day_shift_hours=0
            )
        if leave_hours > 0:
            TimeEntryFactory(resource=resource, date=date_obj, task=None, leave_hours=leave_hours, day_shift_hours=0)

        time_entry_data = {'dates': [date_str], 'taskId': task_1.pk, 'resourceId': resource.pk, 'auto_fill': True}
        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        entry = TimeEntry.objects.get(resource=resource, date=date_obj, task=task_1)
        assert entry.day_shift_hours == Decimal(str(task_1_hours)) + Decimal(str(expected_autofill))

    @pytest.mark.parametrize(
        'hours_key', (pytest.param(key, id=kind) for key, kind in zip(_day_entry_keys, _day_entry_kinds, strict=True))
    )
    def test_rejects_time_entries_with_day_shift_and_absence_hours(self, hours_key, admin_user, api_client):
        task = TaskFactory()

        time_entry_data = {
            'dates': ['2024-01-01'],
            'dayShiftHours': 8,
            'taskId': task.pk,
            'resourceId': task.resource.pk,
            hours_key: 2,
        }

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not TimeEntry.objects.filter(task=task).exists()

    @pytest.mark.parametrize(
        (
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'special_leave_hours',
            'with_reason',
            'expected_status_code',
        ),
        (
            pytest.param(8, 0, 0, 0, None, status.HTTP_201_CREATED, id='sick'),
            pytest.param(0, 8, 0, 0, None, status.HTTP_201_CREATED, id='holiday'),
            pytest.param(0, 0, 4, 0, False, status.HTTP_201_CREATED, id='leave'),
            pytest.param(0, 0, 0, 4, True, status.HTTP_201_CREATED, id='special_leave'),
            pytest.param(0, 0, 4, 4, True, status.HTTP_201_CREATED, id='special_leave_and_leaves'),
            pytest.param(8, 8, 0, 0, None, status.HTTP_400_BAD_REQUEST, id='sick_and_holiday'),
            pytest.param(8, 0, 4, 0, False, status.HTTP_400_BAD_REQUEST, id='sick_and_leave'),
            pytest.param(
                8,
                0,
                0,
                4,
                True,
                status.HTTP_400_BAD_REQUEST,
                id='sick_and_special_leave',
            ),
            pytest.param(0, 8, 0, 4, False, status.HTTP_400_BAD_REQUEST, id='holiday_and_leave'),
            pytest.param(
                0,
                8,
                0,
                4,
                True,
                status.HTTP_400_BAD_REQUEST,
                id='holiday_and_special_leave',
            ),
            pytest.param(8, 8, 4, 0, False, status.HTTP_400_BAD_REQUEST, id='all_non_special'),
            pytest.param(8, 8, 0, 4, True, status.HTTP_400_BAD_REQUEST, id='all_special'),
        ),
    )
    def test_accepts_time_entries_with_only_one_absence_kind(
        self,
        sick_hours,
        holiday_hours,
        leave_hours,
        special_leave_hours,
        with_reason,
        expected_status_code,
        admin_user,
        api_client,
    ):
        resource = ResourceFactory()
        reason = SpecialLeaveReasonFactory()
        time_entry_data = {
            'dates': ['2024-01-02'],
            'dayShiftHours': 0,
            'sickHours': sick_hours,
            'holidayHours': holiday_hours,
            'leaveHours': leave_hours,
            'specialLeaveReason': reason.pk if with_reason else None,
            'specialLeaveHours': special_leave_hours,
            'comment': 'approved',
            'resourceId': resource.pk,
        }

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == expected_status_code
        created = response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(resource=resource).exists() is created

    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
    )
    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'dayShiftHours': 8}, id='day_shift'),
            pytest.param(
                {'dayShiftHours': 4, 'travelHours': 2, 'onCallHours': 3, 'nightShiftHours': 1},
                id='all_task_hours',
            ),
        ),
    )
    def test_accepts_task_entries_for_multiple_days(self, hours_data, admin_user, api_client):
        task = TaskFactory()

        time_entry_data = {
            'dates': [f'2024-01-{day:02}' for day in range(7, 12)],
            'taskId': task.pk,
            'resourceId': task.resource.pk,
        } | hours_data
        # sanity check: ensure we have day shift hours so we can save
        # the new instances
        # NOTE: dict.setdefault() only sets a new value if the key is missing
        time_entry_data.setdefault('dayShiftHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        instances = TimeEntry.objects.filter(task=task)
        assert instances.count() == 5
        assert set(instances.values_list('date', flat=True)) == {datetime.date(2024, 1, day) for day in range(7, 12)}

    @override_config(
        DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
    )
    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'sickHours': 8}, id='sick'),
            pytest.param({'holidayHours': 8}, id='holiday'),
            pytest.param({'leaveHours': 4}, id='leave'),
            pytest.param({'specialLeaveHours': 4, 'specialLeaveReason': 'Add a reason'}, id='special_leave'),
        ),
    )
    def test_accepts_day_entries_for_multiple_days(self, hours_data, admin_user, api_client):
        resource = ResourceFactory()

        # replace the placeholder for special leaves with a valid reason
        if hours_data.get('specialLeaveReason'):
            hours_data['specialLeaveReason'] = SpecialLeaveReasonFactory(title='Test reason').pk

        time_entry_data = {
            'dates': [f'2024-01-{day:02}' for day in range(8, 13)],
            'resourceId': resource.pk,
            'comment': 'approved',
        } | hours_data
        # ensure we have day shift hours so we can save the new instances
        time_entry_data.setdefault('dayShiftHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        instances = TimeEntry.objects.filter(resource=resource)
        assert instances.count() == 5
        assert set(instances.values_list('date', flat=True)) == {datetime.date(2024, 1, day) for day in range(8, 13)}

    def test_rejects_new_time_entries_summing_up_to_more_than_24_hours(self, admin_user, api_client):
        today = datetime.date(2024, 1, 1)
        resource = ResourceFactory()
        start_date = datetime.date(2023, 1, 1)

        project = ProjectFactory(start_date=start_date)
        first_task = TaskFactory(
            title='First',
            resource=resource,
            project=project,
            start_date=start_date,
            end_date=datetime.date(2025, 12, 31),
        )
        second_task = TaskFactory(
            title='Second',
            resource=resource,
            project=project,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )

        # we made some work on the first task
        TimeEntryFactory(resource=resource, task=first_task, date=today, day_shift_hours=6)
        # ... but had to do lots of night time work on the second
        TimeEntryFactory(resource=resource, task=second_task, date=today, day_shift_hours=2, night_shift_hours=6)

        # to hell with it, let's log some paid leave to get back at the
        # company! Take that, company! :^)
        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': [today.isoformat()],
                'resourceId': resource.id,
                'dayShiftHours': 0,
                # we are now over 24h
                'leaveHours': 12,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_overwrites_time_entry_if_total_hours_of_old_and_new_entry_exceeds_24_hours(self, admin_user, api_client):
        """Regression test for Taiga issue #42.

        Single task case.
        """
        today = datetime.date(2024, 1, 1)
        resource = ResourceFactory()
        task = TaskFactory(resource=resource)

        # we made a mistake and inadvertently saved too many hours... oops :^)
        _wrong_time_entry = TimeEntryFactory(resource=resource, task=task, date=today, day_shift_hours=16)

        # let's correct it
        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': [today.isoformat()],
                'taskId': task.id,
                'resourceId': resource.id,
                'dayShiftHours': 10,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        total_hours_today = sum(
            entry.total_hours for entry in TimeEntry.objects.filter(date=today, resource=resource, task=task)
        )
        assert total_hours_today < 24

    def test_rejects_single_time_entry_with_more_than_24_hours(self, admin_user, api_client):
        task = TaskFactory()

        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': ['2024-01-01'],
                'taskId': task.id,
                'resourceId': task.resource.id,
                'dayShiftHours': 30,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        'key', (pytest.param(key, id=kind) for key, kind in zip(_all_hours_keys, _all_hours_kinds, strict=True))
    )
    def test_reject_entry_with_negative_hours(self, key, admin_user, api_client):
        task = TaskFactory()
        data = {
            'dates': ['2024-01-01'],
            'taskId': None if any(key.startswith(prefix) for prefix in ('sick', 'holiday', 'leave')) else task.id,
            'resourceId': task.resource.id,
        } | {key: -1}
        data.setdefault('dayShiftHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        'hours_key, hours_field',
        (
            pytest.param(key, f'{kind}_hours', id=kind)
            for key, kind in zip(_day_entry_keys, _day_entry_kinds, strict=True)
        ),
    )
    def test_overwrites_day_entry_with_another_day_entry_on_same_date(
        self, hours_key, hours_field, admin_user, api_client
    ):
        resource = ResourceFactory()
        target_date = datetime.date(2024, 1, 2)
        existing_day_entry = TimeEntryFactory(resource=resource, date=target_date, sick_hours=8, day_shift_hours=0)

        data = {
            'dates': [target_date.isoformat()],
            'resourceId': resource.pk,
            'dayShiftHours': 0,
            # NOTE: make sure to reset sick hours before updating
            'sickHours': 0,
        } | {hours_key: 8}

        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        existing_day_entry = TimeEntry.objects.get(resource=resource, date=target_date, task__isnull=True)
        assert getattr(existing_day_entry, hours_field) == 8

    @pytest.mark.parametrize(
        'hours_key, hours_field',
        (
            pytest.param(key, f'{kind}_hours', id=kind)
            for key, kind in zip(_task_entry_keys, _task_entry_kinds, strict=True)
        ),
    )
    def test_overwrites_task_entry_for_task_with_existing_task_entry_on_same_date(
        self, hours_key, hours_field, admin_user, api_client
    ):
        resource = ResourceFactory()
        target_date = datetime.date(2024, 1, 2)
        target_task = TaskFactory(title='target', resource=resource)
        other_task = TaskFactory(title='other', resource=resource)
        existing_entry_on_target_task = TimeEntryFactory(
            resource=resource, date=target_date, task=target_task, day_shift_hours=4
        )

        # we can accept a new time entry on an "empty" task
        data = {'dates': [target_date.isoformat()], 'resourceId': resource.pk, 'taskId': other_task.pk, hours_key: 4}
        data.setdefault('dayShiftHours', 0)
        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # we MUST override any existing entry
        data = {'dates': [target_date.isoformat()], 'resourceId': resource.pk, 'taskId': target_task.pk, hours_key: 4}
        data.setdefault('dayShiftHours', 0)
        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        existing_entry_on_target_task.refresh_from_db()
        if hours_field != 'day_shift_hours':
            assert existing_entry_on_target_task.day_shift_hours == 0
        assert getattr(existing_entry_on_target_task, hours_field) == 4

    @pytest.mark.parametrize(
        'hours_key, hours_field',
        (
            pytest.param(key, f'{kind}_hours', id=kind)
            for key, kind in zip(_day_entry_keys, _day_entry_kinds, strict=True)
        ),
    )
    def test_day_entry_overwrites_task_entries_on_same_day_if_not_leave_or_rest(
        self, hours_key, hours_field, admin_user, api_client
    ):
        resource = ResourceFactory()
        target_date = datetime.date(2024, 1, 2)
        task = TaskFactory(title='Should end up without task entries', resource=resource)
        existing_task_entry = TimeEntryFactory(resource=resource, date=target_date, task=task, day_shift_hours=4)
        existing_task_entry_id = existing_task_entry.pk

        data = {
            'dates': [target_date.isoformat()],
            'resourceId': resource.pk,
            'comment': 'approved',
            'dayShiftHours': 0,
        } | {hours_key: 4 if hours_key.removesuffix('Hours') in ('leave', 'rest') else 8}

        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        should_raise_on_getting_deleted_record = (
            does_not_raise() if hours_field in ('leave_hours', 'rest_hours') else pytest.raises(TimeEntry.DoesNotExist)
        )
        with should_raise_on_getting_deleted_record:
            TimeEntry.objects.get(pk=existing_task_entry_id)

    @pytest.mark.parametrize(
        'hours_key',
        (pytest.param(key, id=kind) for key, kind in zip(_task_entry_keys, _task_entry_kinds, strict=True)),
    )
    @pytest.mark.parametrize(
        'existing_hours_field', (pytest.param(f'{kind}_hours', id=kind) for kind in _day_entry_kinds)
    )
    def test_task_entry_overwrites_non_leave_day_entry_on_same_day(
        self, hours_key, existing_hours_field, admin_user, api_client
    ):
        resource = ResourceFactory()
        target_date = datetime.date(2024, 1, 2)

        existing_day_entry = TimeEntryFactory(
            resource=resource, date=target_date, day_shift_hours=0, **{existing_hours_field: 4}
        )
        existing_day_entry_id = existing_day_entry.pk

        target_task = TaskFactory(resource=resource)

        data = {'dates': [target_date.isoformat()], 'resourceId': resource.pk, 'taskId': target_task.pk, hours_key: 4}
        data.setdefault('dayShiftHours', 0)
        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        should_raise_on_getting_deleted_record = (
            does_not_raise() if existing_hours_field == 'leave_hours' else pytest.raises(TimeEntry.DoesNotExist)
        )
        with should_raise_on_getting_deleted_record:
            TimeEntry.objects.get(pk=existing_day_entry_id)

    @pytest.mark.parametrize(
        ('permissions', 'expected_status_code'),
        [
            pytest.param([], status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param(
                ['manage_any_project'], status.HTTP_403_FORBIDDEN, id='project_manager_without_timesheet_perms'
            ),
            pytest.param(['view_any_project'], status.HTTP_403_FORBIDDEN, id='project_viewer_without_timesheet_perms'),
            pytest.param(
                ['view_any_project', 'view_any_timesheet'],
                status.HTTP_403_FORBIDDEN,
                id='project_viewer_and_timesheet_viewer',
            ),
            pytest.param(
                ['view_any_project', 'manage_any_timesheet'],
                status.HTTP_201_CREATED,
                id='project_viewer_and_timesheet_manager',
            ),
            pytest.param(
                ['manage_any_project', 'view_any_timesheet'],
                status.HTTP_403_FORBIDDEN,
                id='project_manager_and_timesheet_viewer',
            ),
            pytest.param(
                ['manage_any_project', 'manage_any_timesheet'],
                status.HTTP_201_CREATED,
                id='project_manager_and_timesheet_manager',
            ),
        ],
    )
    def test_regular_user_has_restricted_write_access_to_time_entries(
        self, permissions, expected_status_code, regular_user, api_client
    ):
        """Verify that users can only write time entries on their own timesheet.

        Also verify that users can write time entries on someeone else's
        timesheet if they have:
        - at least read-only permissions on projects (so they can see
          tasks);
        - read/write permissions on timesheets.
        """
        own_resource = ResourceFactory(user=regular_user)
        own_task = TaskFactory(resource=own_resource)

        for permission in permissions:
            regular_user.user_permissions.add(Permission.objects.get(codename=permission))

        other_user = UserFactory()
        other_resource = ResourceFactory(user=other_user)
        other_task = TaskFactory(resource=other_resource)

        entry_data = {'dates': ['2024-01-01'], 'dayShiftHours': 4}

        client = api_client(user=regular_user)
        # you should be able to create entries for your own tasks
        own_response = client.post(
            self.url(), data=entry_data | {'taskId': own_task.id, 'resourceId': own_resource.id}, format='json'
        )
        assert own_response.status_code == status.HTTP_201_CREATED

        # you should be unable to create entries for other people's
        # tasks unless you have the appropriate permissions
        other_response = client.post(
            self.url(), data=entry_data | {'taskId': other_task.id, 'resourceId': other_resource.id}, format='json'
        )
        assert other_response.status_code == expected_status_code

    @django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
    def test_sends_holiday_event_when_holiday_is_logged(self, admin_user, api_client, caplog):
        resource = ResourceFactory(user=admin_user)
        task = TaskFactory(resource=resource)

        day_shift_entry_data = {
            'dates': ['2024-01-01'],
            'dayShiftHours': 4,
            'taskId': task.id,
            'resourceId': resource.id,
        }
        with caplog.at_level(logging.DEBUG):
            api_client(user=admin_user).post(self.url(), data=day_shift_entry_data, format='json')
        assert not caplog.records

        holiday_entry_data = {'dates': ['2024-01-02'], 'dayShiftHours': 0, 'holidayHours': 8, 'resourceId': resource.id}
        with caplog.at_level(logging.DEBUG):
            api_client(user=admin_user).post(self.url(), data=holiday_entry_data, format='json')
        assert len(caplog.records) == 1
        expected_event_payload = {
            'resource': {'name': resource.full_name, 'email': resource.user.email},
            'start_date': '2024-01-02',
            'end_date': '2024-01-02',
        }
        _, _, message = caplog.record_tuples[0]
        event_sent_log, payload_sent_log = message.split('. ', 1)
        assert event_sent_log == 'Event "holidays" sent'
        assert payload_sent_log == f'Payload: {expected_event_payload}'

    @django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
    def test_sends_holiday_event_with_start_and_end_dates(self, admin_user, api_client, caplog):
        resource = ResourceFactory(user=admin_user)

        holiday_entry_data = {
            'dates': ['2024-01-03', '2024-01-01', '2024-01-04', '2024-01-02'],
            'dayShiftHours': 0,
            'holidayHours': 8,
            'resourceId': resource.id,
        }
        with caplog.at_level(logging.DEBUG):
            api_client(user=admin_user).post(self.url(), data=holiday_entry_data, format='json')
        assert len(caplog.records) == 1
        expected_event_payload = {
            'resource': {'name': resource.full_name, 'email': resource.user.email},
            'start_date': '2024-01-01',
            'end_date': '2024-01-04',
        }
        _, _, message = caplog.record_tuples[0]
        assert str(expected_event_payload) in message


class TestTimeEntryClearAPIAction:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-time-entry-clear')

    def test_rejects_empty_list_of_time_entry_ids(self, admin_user, api_client):
        response = api_client(user=admin_user).post(self.url(), data={}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_time_entry_ids_not_in_a_list(self, admin_user, api_client):
        entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
        response = api_client(user=admin_user).post(self.url(), data={'ids': entry.id}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_deletion_of_closed_time_entries(self, admin_user, api_client):
        open_entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory(), date=datetime.date(2020, 6, 1))

        TimesheetSubmissionFactory(
            resource=open_entry.task.resource, period=(datetime.date(2020, 4, 1), datetime.date(2020, 5, 1))
        )
        # Timesheet is being assigned to closed entry via 'link_to_timesheet' - Timeentry pre-save signal
        with pytest.raises(exceptions.ValidationError, match='Cannot modify time entries for submitted timesheets'):
            TimeEntryFactory(
                resource=open_entry.task.resource,
                day_shift_hours=8,
                task=TaskFactory(),
                date=datetime.date(2020, 4, 15),
            )

    def test_admin_can_clear_any_time_entry(self, admin_user, api_client):
        day_entry = TimeEntryFactory(date=datetime.date(2024, 1, 1), day_shift_hours=0, sick_hours=8)
        task_entry = TimeEntryFactory(date=datetime.date(2024, 1, 2), day_shift_hours=8, task=TaskFactory())
        assert TimeEntry.objects.exists()
        response = api_client(user=admin_user).post(
            self.url(), data={'ids': [day_entry.pk, task_entry.pk]}, format='json'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TimeEntry.objects.exists()

    @pytest.mark.parametrize(
        ('permissions', 'expected_status_code'),
        [
            pytest.param([], status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param(
                ['manage_any_project'], status.HTTP_403_FORBIDDEN, id='project_manager_without_timesheet_perms'
            ),
            pytest.param(['view_any_project'], status.HTTP_403_FORBIDDEN, id='project_viewer_without_timesheet_perms'),
            pytest.param(
                ['view_any_project', 'view_any_timesheet'],
                status.HTTP_403_FORBIDDEN,
                id='project_viewer_and_timesheet_viewer',
            ),
            pytest.param(
                ['view_any_project', 'manage_any_timesheet'],
                status.HTTP_204_NO_CONTENT,
                id='project_viewer_and_timesheet_manager',
            ),
            pytest.param(
                ['manage_any_project', 'view_any_timesheet'],
                status.HTTP_403_FORBIDDEN,
                id='project_manager_and_timesheet_viewer',
            ),
            pytest.param(
                ['manage_any_project', 'manage_any_timesheet'],
                status.HTTP_204_NO_CONTENT,
                id='project_manager_and_timesheet_manager',
            ),
        ],
    )
    def test_regular_user_can_only_clear_allowed_time_entries(
        self, permissions, expected_status_code, regular_user, api_client
    ):
        user_resource = ResourceFactory(user=regular_user)
        other_user_resource = ResourceFactory()

        for permission in permissions:
            regular_user.user_permissions.add(Permission.objects.get(codename=permission))

        entry = TimeEntryFactory(
            date=datetime.date(2024, 1, 1), day_shift_hours=0, sick_hours=8, resource=user_resource
        )
        other_entry = TimeEntryFactory(
            date=datetime.date(2024, 1, 1), day_shift_hours=0, sick_hours=8, resource=other_user_resource
        )

        response = api_client(user=regular_user).post(
            self.url(), data={'ids': [entry.pk, other_entry.pk]}, format='json'
        )
        assert response.status_code == expected_status_code

        # if we were able to delete both entries before then we have
        # nothing to delete
        if expected_status_code < 400:
            response = api_client(user=regular_user).post(self.url(), data={'ids': [entry.pk]}, format='json')
            assert response.status_code == status.HTTP_204_NO_CONTENT


class TestSpecialLeaveReasonViewSet:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-special-leave-reason-list')

    def test_returns_valid_reasons_in_limited_interval(self, admin_user, api_client):
        interval_start = datetime.date(2024, 1, 1)
        interval_end = datetime.date(2024, 1, 31)

        # this one is obvious
        always_valid = SpecialLeaveReasonFactory(title='always')
        # starts before our interval's start and doesn't end? it's ok
        valid_since_earlier_date = SpecialLeaveReasonFactory(title='since 1990', from_date=datetime.date(1990, 1, 1))
        # this validity period fully contains our interval, so it's valid
        encompassing_interval = SpecialLeaveReasonFactory(
            title='definitely valid', from_date=datetime.date(2010, 1, 1), to_date=datetime.date(2030, 1, 1)
        )
        # on the other hand, we don't want this one, as we can accept
        # the reason only in a part of our interval
        _fully_contained_within_interval = SpecialLeaveReasonFactory(
            title='contained', from_date=datetime.date(2024, 1, 10), to_date=datetime.date(2024, 1, 15)
        )
        # not expired yet, still good
        valid_until_future_date = SpecialLeaveReasonFactory(title='until 2030', to_date=datetime.date(2030, 1, 1))
        # not started, we don't want it
        _not_valid_yet = SpecialLeaveReasonFactory(title='not valid yet', from_date=datetime.date(2027, 1, 1))
        # throw it away, it's long expired
        _expired = SpecialLeaveReasonFactory(title='stale and moldy', to_date=datetime.date(2018, 1, 1))
        # partial overlap, we don't want it - see above
        _expiring_within_interval = SpecialLeaveReasonFactory(title='expiring', to_date=datetime.date(2024, 1, 5))
        _starting_within_interval = SpecialLeaveReasonFactory(title='starting', from_date=datetime.date(2024, 1, 25))

        response = api_client(user=admin_user).get(
            self.url(), data={'from': interval_start.isoformat(), 'to': interval_end.isoformat()}
        )
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item.get('id') for item in response.json()]
        assert returned_ids == [
            always_valid.id,
            valid_since_earlier_date.id,
            encompassing_interval.id,
            valid_until_future_date.id,
        ]

    def test_returns_all_reasons_if_no_interval_provided(self, admin_user, api_client):
        always_valid = SpecialLeaveReasonFactory(title='always')
        with_start_date = SpecialLeaveReasonFactory(title='since 1990', from_date=datetime.date(1990, 1, 1))
        with_end_date = SpecialLeaveReasonFactory(title='until 2030', to_date=datetime.date(2030, 1, 1))
        limited_validity_period = SpecialLeaveReasonFactory(
            title='definitely valid', from_date=datetime.date(2010, 1, 1), to_date=datetime.date(2030, 1, 1)
        )

        response = api_client(user=admin_user).get(self.url())
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item.get('id') for item in response.json()]
        assert returned_ids == [
            always_valid.id,
            with_start_date.id,
            with_end_date.id,
            limited_validity_period.id,
        ]

    @pytest.mark.parametrize('query_param', ('from', 'to'))
    def test_rejects_requests_with_only_one_of_from_and_to(self, query_param, admin_user, api_client):
        SpecialLeaveReasonFactory(title='should not be returned')
        response = api_client(user=admin_user).get(self.url(), data={query_param: '2024-01-01'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
