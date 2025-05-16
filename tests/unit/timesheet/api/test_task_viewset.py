from contextlib import nullcontext as does_not_raise
import datetime
import typing
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from testutils.factories import ResourceFactory, TaskFactory, TimeEntryFactory, UserFactory
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TimeEntry
from krm3.core.models.timesheets import TimeEntryState

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Task


_day_entry_kinds = ('sick', 'holiday', 'leave')
_day_entry_keys = tuple(f'{key}Hours' for key in _day_entry_kinds)

_task_entry_kinds = ('day_shift', 'night_shift', 'rest', 'travel')
_task_entry_keys = ('dayShiftHours', 'nightShiftHours', 'restHours', 'travelHours')

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
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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

    @pytest.mark.parametrize(
        'task_end_date',
        (pytest.param(datetime.date(2024, 12, 31), id='known_end'), pytest.param(None, id='open_ended')),
    )
    def test_returns_valid_time_entry_data(self, task_end_date, admin_user, api_client):
        task_start_date = datetime.date(2023, 1, 1)

        time_entry_start_date = datetime.date(2024, 1, 1)
        time_entry_end_date = datetime.date(2024, 1, 7)

        resource: Resource = ResourceFactory()
        task: 'Task' = TaskFactory(resource=resource, start_date=task_start_date, end_date=task_end_date)

        def _make_time_entry(**kwargs):
            return TimeEntryFactory(task=kwargs.pop('task', task), resource=resource, **kwargs)

        date_within_range = datetime.date(2024, 1, 3)

        _early_time_entry = _make_time_entry(date=datetime.date(2023, 7, 1), comment='Too early')
        _late_time_entry = _make_time_entry(date=datetime.date(2024, 7, 1), comment='Too late')
        task_entry_within_range = _make_time_entry(date=date_within_range, comment='Within range')
        day_entry_within_range = _make_time_entry(
            date=date_within_range, task=None, day_shift_hours=0, leave_hours=2, comment='Within range (day)'
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

        def _as_quantized_decimal(n: int | float | Decimal) -> str:
            return str(Decimal(n).quantize(Decimal('1.00')))

        assert response.json() == {
            'tasks': [
                {
                    'id': task.pk,
                    'title': task.title,
                    'basketTitle': task.basket_title,
                    'color': task.color,
                    'startDate': task_start_date.isoformat(),
                    'endDate': task_end_date.isoformat() if task_end_date else None,
                    'projectName': task.project.name,
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
                    'nightShiftHours': _as_quantized_decimal(task_entry_within_range.night_shift_hours),
                    'onCallHours': _as_quantized_decimal(task_entry_within_range.on_call_hours),
                    'travelHours': _as_quantized_decimal(task_entry_within_range.travel_hours),
                    'restHours': _as_quantized_decimal(task_entry_within_range.rest_hours),
                    'state': str(task_entry_within_range.state),
                    'comment': 'Within range',
                    'task': task.pk,
                },
                {
                    'id': day_entry_within_range.id,
                    'date': date_within_range.isoformat(),
                    'lastModified': day_entry_within_range.last_modified.isoformat(),
                    'dayShiftHours': _as_quantized_decimal(day_entry_within_range.day_shift_hours),
                    'sickHours': _as_quantized_decimal(day_entry_within_range.sick_hours),
                    'holidayHours': _as_quantized_decimal(day_entry_within_range.holiday_hours),
                    'leaveHours': _as_quantized_decimal(day_entry_within_range.leave_hours),
                    'nightShiftHours': _as_quantized_decimal(day_entry_within_range.night_shift_hours),
                    'onCallHours': _as_quantized_decimal(day_entry_within_range.on_call_hours),
                    'travelHours': _as_quantized_decimal(day_entry_within_range.travel_hours),
                    'restHours': _as_quantized_decimal(day_entry_within_range.rest_hours),
                    'state': str(day_entry_within_range.state),
                    'comment': 'Within range (day)',
                    'task': None,
                },
            ],
        }

    def test_picks_only_ongoing_tasks(self, admin_user, api_client):
        time_entry_start_date = datetime.date(2024, 1, 1)
        time_entry_end_date = datetime.date(2024, 1, 7)

        resource: 'Resource' = ResourceFactory()

        _expired_task = TaskFactory(
            resource=resource, start_date=datetime.date(2022, 1, 1), end_date=datetime.date(2023, 12, 31)
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

        user_task = TaskFactory(resource=user_resource, start_date=start_date, end_date=end_date)
        other_user_task = TaskFactory(resource=other_user_resource, start_date=start_date, end_date=end_date)

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
        ('permission', 'expected_status_code'),
        [
            pytest.param(None, status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param('manage_any_project', status.HTTP_200_OK, id='project_manager'),
            pytest.param('manage_any_timesheet', status.HTTP_403_FORBIDDEN, id='timesheet_manager'),
            pytest.param('view_any_project', status.HTTP_200_OK, id='project_viewer'),
            pytest.param('view_any_timesheet', status.HTTP_403_FORBIDDEN, id='timesheet_viewer'),
        ],
    )
    def test_regular_user_can_see_tasks_based_on_permissions(
        self, permission, expected_status_code, regular_user, api_client
    ):
        user_resource = ResourceFactory(user=regular_user)
        other_user_resource = ResourceFactory()

        if permission:
            regular_user.user_permissions.add(Permission.objects.get(codename=permission))

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2025, 1, 1)

        user_task = TaskFactory(resource=user_resource, start_date=start_date, end_date=end_date)
        other_user_task = TaskFactory(resource=other_user_resource, start_date=start_date, end_date=end_date)

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
                {'nightShiftHours': 1, 'onCallHours': 1, 'travelHours': 0.5, 'restHours': 1},
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
        time_entry_data = {'dates': ['2024-01-01'], 'dayShiftHours': 0, 'resourceId': resource.pk} | hours_data

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(resource=resource).exists()

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
        ('sick_hours', 'holiday_hours', 'leave_hours', 'expected_status_code'),
        (
            pytest.param(8, 0, 0, status.HTTP_201_CREATED, id='sick'),
            pytest.param(0, 8, 0, status.HTTP_201_CREATED, id='holiday'),
            pytest.param(0, 0, 4, status.HTTP_201_CREATED, id='leave'),
            pytest.param(8, 8, 0, status.HTTP_400_BAD_REQUEST, id='sick_and_holiday'),
            pytest.param(8, 0, 4, status.HTTP_400_BAD_REQUEST, id='sick_and_leave'),
            pytest.param(0, 8, 4, status.HTTP_400_BAD_REQUEST, id='holiday_and_leave'),
            pytest.param(8, 8, 4, status.HTTP_400_BAD_REQUEST, id='all'),
        ),
    )
    def test_accepts_time_entries_with_only_one_absence_kind(
        self, sick_hours, holiday_hours, expected_status_code, leave_hours, admin_user, api_client
    ):
        resource = ResourceFactory()
        time_entry_data = {
            'dates': ['2024-01-01'],
            'dayShiftHours': 0,
            'sickHours': sick_hours,
            'holidayHours': holiday_hours,
            'leaveHours': leave_hours,
            'resourceId': resource.pk,
        }

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == expected_status_code
        created = response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(resource=resource).exists() is created

    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'dayShiftHours': 8}, id='day_shift'),
            pytest.param(
                {'dayShiftHours': 4, 'travelHours': 2, 'restHours': 2, 'onCallHours': 3, 'nightShiftHours': 1},
                id='all_task_hours',
            ),
        ),
    )
    def test_accepts_task_entries_for_multiple_days(self, hours_data, admin_user, api_client):
        task = TaskFactory()

        time_entry_data = {
            'dates': [f'2024-01-{day:02}' for day in range(1, 6)],
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
        assert set(instances.values_list('date', flat=True)) == {datetime.date(2024, 1, day) for day in range(1, 6)}

    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'sickHours': 8}, id='sick'),
            pytest.param({'holidayHours': 8}, id='holiday'),
            pytest.param({'leaveHours': 4}, id='leave'),
        ),
    )
    def test_accepts_day_entries_for_multiple_days(self, hours_data, admin_user, api_client):
        resource = ResourceFactory()

        time_entry_data = {
            'dates': [f'2024-01-{day:02}' for day in range(1, 6)],
            'resourceId': resource.pk,
        } | hours_data
        # ensure we have day shift hours so we can save the new instances
        time_entry_data.setdefault('dayShiftHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        instances = TimeEntry.objects.filter(resource=resource)
        assert instances.count() == 5
        assert set(instances.values_list('date', flat=True)) == {datetime.date(2024, 1, day) for day in range(1, 6)}

    def test_rejects_new_time_entries_summing_up_to_more_than_24_hours(self, admin_user, api_client):
        today = datetime.date(2024, 1, 1)
        resource = ResourceFactory()

        first_task = TaskFactory(
            title='First', resource=resource, start_date=datetime.date(2023, 1, 1), end_date=datetime.date(2025, 12, 31)
        )
        second_task = TaskFactory(
            title='Second',
            resource=resource,
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

        # we made a mistake and inadvertently saved 18 hours... oops :^)
        _wrong_time_entry = TimeEntryFactory(resource=resource, task=task, date=today, day_shift_hours=18)

        # let's correct it
        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': [today.isoformat()],
                'taskId': task.id,
                'resourceId': resource.id,
                'dayShiftHours': 8,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        total_hours_today = sum(
            entry.total_hours for entry in TimeEntry.objects.filter(date=today, resource=resource, task=task)
        )
        assert total_hours_today < 24

    @pytest.mark.parametrize(
        'hours_key',
        (pytest.param(key, id=kind) for key, kind in zip(_day_entry_keys, _day_entry_kinds, strict=True)),
    )
    def test_overwrites_day_entry_keeping_total_hours_under_24_hours(self, hours_key, admin_user, api_client):
        """Regression test for Taiga issue #42.

        In this case, another day entry exists.
        """
        today = datetime.date(2024, 1, 1)
        resource = ResourceFactory()
        task = TaskFactory(resource=resource)

        # we made a mistake and inadvertently saved 18 hours... oops :^)
        _wrong_day_entry = TimeEntryFactory(resource=resource, task=None, date=today, day_shift_hours=0, leave_hours=18)
        _task_entry = TimeEntryFactory(resource=resource, task=task, date=today, day_shift_hours=2)

        # let's correct it
        response = api_client(user=admin_user).post(
            self.url(),
            data={'dates': [today.isoformat()], 'resourceId': resource.id, 'dayShiftHours': 0, hours_key: 6},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        total_hours_today = sum(
            entry.total_hours for entry in TimeEntry.objects.filter(date=today, resource=resource, task=task)
        )
        assert total_hours_today < 24

    @pytest.mark.parametrize(
        'hours_key',
        (pytest.param(key, id=kind) for key, kind in zip(_task_entry_keys, _task_entry_kinds, strict=True)),
    )
    def test_overwrites_task_entry_on_same_task_keeping_total_hours_under_24_hours(
        self, hours_key, admin_user, api_client
    ):
        """Regression test for Taiga issue #42.

        In this case, another day entry exists.
        """
        today = datetime.date(2024, 1, 1)
        resource = ResourceFactory()
        task = TaskFactory(resource=resource, title='target')
        other_task = TaskFactory(resource=resource, title='other')
        _task_entry_on_other_task = TimeEntryFactory(resource=resource, task=other_task, date=today, day_shift_hours=2)

        # we made a mistake and inadvertently saved 18 hours... oops :^)
        _wrong_task_entry = TimeEntryFactory(resource=resource, task=task, date=today, day_shift_hours=18)

        # let's correct it
        response = api_client(user=admin_user).post(
            self.url(),
            data={'dates': [today.isoformat()], 'resourceId': resource.id, 'taskId': task.id, 'dayShiftHours': 0}
            | {hours_key: 6},
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
        target_date = datetime.date(2024, 1, 1)
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
        existing_day_entry.refresh_from_db()
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
        target_date = datetime.date(2024, 1, 1)
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
    def test_non_leave_day_entry_overwrites_task_entries_on_same_day(
        self, hours_key, hours_field, admin_user, api_client
    ):
        resource = ResourceFactory()
        target_date = datetime.date(2024, 1, 1)
        task = TaskFactory(title='Should end up without task entries', resource=resource)
        existing_task_entry = TimeEntryFactory(resource=resource, date=target_date, task=task, day_shift_hours=4)
        existing_task_entry_id = existing_task_entry.pk

        data = {
            'dates': [target_date.isoformat()],
            'resourceId': resource.pk,
            'dayShiftHours': 0,
        } | {hours_key: 8}

        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        should_raise_on_getting_deleted_record = (
            does_not_raise() if hours_field == 'leave_hours' else pytest.raises(TimeEntry.DoesNotExist)
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
        target_date = datetime.date(2024, 1, 1)

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
        ('permission', 'expected_status_code'),
        [
            pytest.param(None, status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param('manage_any_project', status.HTTP_201_CREATED, id='project_manager'),
            pytest.param('manage_any_timesheet', status.HTTP_201_CREATED, id='timesheet_manager'),
            pytest.param('view_any_project', status.HTTP_403_FORBIDDEN, id='project_viewer'),
            pytest.param('view_any_timesheet', status.HTTP_403_FORBIDDEN, id='timesheet_viewer'),
        ],
    )
    def test_regular_user_has_restricted_write_access_to_time_entries(
        self, permission, expected_status_code, regular_user, api_client
    ):
        own_resource = ResourceFactory(user=regular_user)
        own_task = TaskFactory(resource=own_resource)

        if permission:
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
        open_entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
        closed_entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory(), state=TimeEntryState.CLOSED)
        response = api_client(user=admin_user).post(
            self.url(), data={'ids': [open_entry.pk, closed_entry.pk]}, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

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
        ('permission', 'expected_status_code'),
        [
            pytest.param(None, status.HTTP_403_FORBIDDEN, id='no_perms'),
            pytest.param('manage_any_project', status.HTTP_204_NO_CONTENT, id='project_manager'),
            pytest.param('manage_any_timesheet', status.HTTP_204_NO_CONTENT, id='timesheet_manager'),
            pytest.param('view_any_project', status.HTTP_403_FORBIDDEN, id='project_viewer'),
            pytest.param('view_any_timesheet', status.HTTP_403_FORBIDDEN, id='timesheet_viewer'),
        ],
    )
    def test_regular_user_can_only_clear_allowed_time_entries(
        self, permission, expected_status_code, regular_user, api_client
    ):
        user_resource = ResourceFactory(user=regular_user)
        other_user_resource = ResourceFactory()

        if permission:
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
