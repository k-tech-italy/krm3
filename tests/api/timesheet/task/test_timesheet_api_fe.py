import pytest
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_201_CREATED

from testutils.factories import TaskFactory


@pytest.fixture
def scenario(resource):
    TaskFactory(contract=True, resource=resource)
    return {
        "resource_id": resource.pk, "day_shift_hours": 4, "night_shift_hours": 3, "travel_hours": 2, "on_call_hours": 1
    }


def test_create_time_entries(scenario, resource, api_client):
    """
    Test creation of Time Entries for a given resource.

    POST /api/v1/timesheet/task-entry/
    {
       "task_id": 7, "day_shift_hours": 3, "night_shift_hours": 3, "travel_hours": 3, "on_call_hours": 3,
       "comment": "asddsasda",
        "dates": ["20260701"]
    }
    --> Return the updated Day Entries and updated Task Entries
    """
    url = reverse('timesheet-api:api-task-entry-list')
    response = api_client(user=resource.user).post(
        url,
        data=scenario | {"dates": ["20260701"]},
        format='json'
    )
    assert response.status_code == HTTP_201_CREATED
    from krm3.core.models import TaskEntry
    assert list(TaskEntry.objects.values_list(
        "day_shift_hours", "night_shift_hours", "on_call_hours", "travel_hours", "comment"
    )) == [
        {}
    ]

    #
    # time_entry_data = {
    #                       'dates': ['2024-01-01'],
    #                       'dayShiftHours': day_shift_hours,
    #                       'taskId': task.pk,
    #                       'resourceId': task.resource.pk,
    #                   } | optional_data
    #
    # response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
    # assert response.status_code == status.HTTP_201_CREATED
    #
    #
    #
    #
    # @pytest.mark.parametrize(
    #     ('day_shift_hours', 'optional_data'),
    #     (
    #         pytest.param(8, {}, id='only_day_shift_hours'),
    #         pytest.param(
    #             1,
    #             {'nightShiftHours': 1, 'onCallHours': 1, 'travelHours': 0.5},
    #             id='task_entry_with_optional_hours',
    #         ),
    #     ),
    # )
    # def test_creates_single_valid_task_entry(self, day_shift_hours, optional_data, admin_user, api_client):
    #     task = TaskFactory()
    #     assert not TimeEntry.objects.filter(task=task).exists()
    #
    #     time_entry_data = {
    #         'dates': ['2024-01-01'],
    #         'dayShiftHours': day_shift_hours,
    #         'taskId': task.pk,
    #         'resourceId': task.resource.pk,
    #     } | optional_data
    #
    #     response = api_client(user=admin_user).post(self.url(), data=time_entry_data, format='json')
    #     assert response.status_code == status.HTTP_201_CREATED
    #     assert TimeEntry.objects.filter(task=task).exists()