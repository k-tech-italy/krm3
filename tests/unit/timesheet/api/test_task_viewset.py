import datetime
import typing
from decimal import Decimal
from django.contrib.auth.models import Permission
import pytest
from rest_framework import status
from rest_framework.reverse import reverse

from factories import ResourceFactory, TaskFactory, TimeEntryFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource
    from krm3.core.models import Task


class TestTaskAPIListView:
    @staticmethod
    def url():
        return reverse('timesheet-api:api-task-list')

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

    def test_returns_valid_time_entry_data(self, admin_user, api_client):
        task_start_date = datetime.date(2023, 1, 1)
        task_end_date = datetime.date(2024, 12, 31)

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
            'endDate': task_end_date.isoformat(),
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
        assert actual_task_ids == {expiring_task.id, ongoing_task.id, starting_midweek_task.id}

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

        user = user_resource.user
        if permission:
            user.user_permissions.add(Permission.objects.get(codename=permission))

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2025, 1, 1)

        user_task = TaskFactory(resource=user_resource, start_date=start_date, end_date=end_date)
        other_user_task = TaskFactory(resource=other_user_resource, start_date=start_date, end_date=end_date)

        client = api_client(user=user)

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
            assert user_response.json()[0].get('id') == other_user_task.id
