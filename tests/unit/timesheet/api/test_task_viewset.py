import datetime
import typing
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from factories import ResourceFactory, TaskFactory, TimeEntryFactory, UserFactory
from rest_framework import status
from rest_framework.reverse import reverse

from krm3.core.models import TimeEntry

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Task


_day_entry_kinds = ('sick', 'holiday', 'leave')
_day_entry_keys = (f'{key}Hours' for key in _day_entry_kinds)

_computed_hours_kinds = (*_day_entry_kinds, 'work', 'overtime', 'rest', 'travel')
_computed_hours_keys = (f'{key}Hours' for key in _computed_hours_kinds)

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
            return TimeEntryFactory(task=task, resource=resource, **kwargs)

        date_within_range = datetime.date(2024, 1, 3)

        _early_time_entry = _make_time_entry(date=datetime.date(2023, 7, 1), comment='Too early')
        _late_time_entry = _make_time_entry(date=datetime.date(2024, 7, 1), comment='Too late')
        time_entry_within_range = _make_time_entry(date=date_within_range, comment='Within range')

        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': resource.pk,
                'start_date': time_entry_start_date.isoformat(),
                'end_date': time_entry_end_date.isoformat(),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # we're dealing with a single task right now...
        data = response.json()
        assert len(data) == 1

        def _as_quantized_decimal(n: int | float | Decimal) -> str:
            return str(Decimal(n).quantize(Decimal('1.00')))

        task_data = data[0]
        assert task_data == {
            'id': task.pk,
            'title': task.title,
            'basketTitle': task.basket_title,
            'color': task.color,
            'startDate': task_start_date.isoformat(),
            'endDate': task_end_date.isoformat() if task_end_date else None,
            'projectName': task.project.name,
            'timeEntries': [
                {
                    'id': time_entry_within_range.id,
                    'date': date_within_range.isoformat(),
                    'lastModified': time_entry_within_range.last_modified.isoformat(),
                    'workHours': _as_quantized_decimal(time_entry_within_range.work_hours),
                    'sickHours': _as_quantized_decimal(time_entry_within_range.sick_hours),
                    'holidayHours': _as_quantized_decimal(time_entry_within_range.holiday_hours),
                    'leaveHours': _as_quantized_decimal(time_entry_within_range.leave_hours),
                    'overtimeHours': _as_quantized_decimal(time_entry_within_range.overtime_hours),
                    'onCallHours': _as_quantized_decimal(time_entry_within_range.on_call_hours),
                    'travelHours': _as_quantized_decimal(time_entry_within_range.travel_hours),
                    'restHours': _as_quantized_decimal(time_entry_within_range.rest_hours),
                    'state': str(time_entry_within_range.state),
                    'comment': 'Within range',
                }
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
            resource=resource, start_date=datetime.date(2023, 1, 1), end_date=datetime.date(2024, 1, 3)
        )
        ongoing_task = TaskFactory(
            resource=resource, start_date=datetime.date(2023, 1, 1), end_date=datetime.date(2024, 12, 31)
        )
        # NOTE: tasks starting within the given range are considered ongoing
        starting_midweek_task = TaskFactory(
            resource=resource, start_date=datetime.date(2024, 1, 4), end_date=datetime.date(2025, 12, 31)
        )
        _future_task = TaskFactory(
            resource=resource, start_date=datetime.date(2032, 1, 1), end_date=datetime.date(2033, 12, 31)
        )
        open_ended_task = TaskFactory(resource=resource, start_date=datetime.date(2022, 1, 1), end_date=None)

        response = api_client(user=admin_user).get(
            self.url(),
            data={
                'resource_id': resource.pk,
                'start_date': time_entry_start_date.isoformat(),
                'end_date': time_entry_end_date.isoformat(),
            },
        )
        assert response.status_code == status.HTTP_200_OK

        actual_task_ids = {task_data.get('id') for task_data in response.json()}
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
        assert user_response.json()[0].get('id') == user_task.id

        other_user_response = client.get(
            self.url(),
            data={
                'resource_id': other_user_resource.pk,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )
        assert other_user_response.status_code == status.HTTP_200_OK
        assert other_user_response.json()[0].get('id') == other_user_task.id

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
        assert user_response.json()[0].get('id') == user_task.id

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
            assert other_user_response.json()[0].get('id') == other_user_task.id


class TestTimeEntryAPICreateView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-time-entry-list')

    @pytest.mark.parametrize(
        ('work_hours', 'optional_data'),
        (
            pytest.param(0, {}, id='no_work'),
            pytest.param(8, {}, id='only_work_hours'),
            pytest.param(
                1,
                {'overtimeHours': 1, 'onCallHours': 1, 'travelHours': 0.5, 'restHours': 1},
                id='task_entry_with_optional_hours',
            ),
            pytest.param(0, {'leaveHours': 2}, id='day_entry_leave'),
            pytest.param(0, {'holidayHours': 8}, id='day_entry_holiday'),
            pytest.param(0, {'sickHours': 8}, id='day_entry_sick'),
        ),
    )
    def test_creates_single_valid_time_entry(self, work_hours, optional_data, admin_user, api_client):
        task = TaskFactory()
        assert not TimeEntry.objects.filter(task=task).exists()

        time_entry_data = {
            'dates': ['2024-01-01'],
            'workHours': work_hours,
            'taskId': task.pk,
            'resourceId': task.resource.pk,
        } | optional_data

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(task=task).exists()

    @pytest.mark.parametrize(
        'hours_key', (pytest.param(key, id=kind) for key, kind in zip(_day_entry_keys, _day_entry_kinds, strict=True))
    )
    def test_rejects_time_entries_with_work_and_absence_hours(self, hours_key, admin_user, api_client):
        task = TaskFactory()

        time_entry_data = {
            'dates': ['2024-01-01'],
            'workHours': 8,
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
        task = TaskFactory()

        time_entry_data = {
            'dates': ['2024-01-01'],
            'workHours': 0,
            'sickHours': sick_hours,
            'holidayHours': holiday_hours,
            'leaveHours': leave_hours,
            'taskId': task.pk,
            'resourceId': task.resource.pk,
        }

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == expected_status_code
        created = response.status_code == status.HTTP_201_CREATED
        assert TimeEntry.objects.filter(task=task).exists() is created

    @pytest.mark.parametrize(
        'hours_data',
        (
            pytest.param({'workHours': 8}, id='work'),
            pytest.param({'sickHours': 8}, id='sick'),
            pytest.param({'holidayHours': 8}, id='holiday'),
            pytest.param({'leaveHours': 4}, id='leave'),
            pytest.param(
                {'workHours': 4, 'travelHours': 2, 'restHours': 2, 'onCallHours': 3, 'overtimeHours': 1},
                id='all_task_hours',
            ),
        ),
    )
    def test_accepts_time_entries_for_multiple_days(self, hours_data, admin_user, api_client):
        task = TaskFactory()

        time_entry_data = {
            'dates': [f'2024-01-{day:02}' for day in range(1, 6)],
            'taskId': task.pk,
            'resourceId': task.resource.pk,
        } | hours_data
        # ensure we have work hours so we can save the new instances
        time_entry_data.setdefault('workHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        instances = TimeEntry.objects.filter(task=task)
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
        absence_task = TaskFactory(
            title='absences',
            resource=resource,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )

        # we made some work on the first task
        TimeEntryFactory(resource=resource, task=first_task, date=today, work_hours=6)
        # ... but had to do lots of overtime on the second
        TimeEntryFactory(resource=resource, task=second_task, date=today, work_hours=2, overtime_hours=6)

        # to hell with it, let's log some paid leave to get back at the
        # company! Take that, company! :^)
        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': [today.isoformat()],
                'taskId': absence_task.id,
                'resourceId': resource.id,
                'workHours': 0,
                # we are now over 24h
                'leaveHours': 12,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_single_time_entry_with_more_than_24_hours(self, admin_user, api_client):
        task = TaskFactory()

        response = api_client(user=admin_user).post(
            self.url(),
            data={
                'dates': ['2024-01-01'],
                'taskId': task.id,
                'resourceId': task.resource.id,
                'workHours': 30,
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
            'taskId': task.id,
            'resourceId': task.resource.id,
        } | {key: -1}
        data.setdefault('workHours', 0)

        response = api_client(user=admin_user).post(self.url(), data=data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

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

        entry_data = {'dates': ['2024-01-01'], 'workHours': 4}

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
