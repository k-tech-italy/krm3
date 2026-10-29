import pytest
from django.urls import reverse
from testutils.factories import TaskFactory
from testutils.permissions import add_permissions

COST_FIELDS = {'work_price', 'travel_price'}


@pytest.mark.parametrize(
    ('permissions', 'expected_visible'),
    [
        pytest.param([], False, id='no-cost-permission'),
        pytest.param(['core.view_any_task_costs'], True, id='view-any-task-costs'),
        pytest.param(['core.manage_any_task_costs'], True, id='manage-any-task-costs'),
        pytest.param(
            ['core.view_any_task_costs', 'core.manage_any_task_costs'], True, id='view-and-manage-any-task-costs'
        ),
    ],
)
def test_task_admin_change_view_shows_costs_only_with_cost_permission(
    client, staff_user, permissions, expected_visible
):
    add_permissions(staff_user, ['core.view_task', 'core.change_task', *permissions])
    task = TaskFactory(contract=True)
    client.force_login(staff_user)

    response = client.get(reverse('admin:core_task_change', args=[task.pk]))

    assert response.status_code == 200
    fields = set(response.context['adminform'].form.fields)
    assert COST_FIELDS.issubset(fields) is expected_visible
    assert fields.isdisjoint(COST_FIELDS) is not expected_visible


def test_task_admin_change_view_shows_costs_to_superuser(admin_client):
    task = TaskFactory(contract=True)

    response = admin_client.get(reverse('admin:core_task_change', args=[task.pk]))

    assert response.status_code == 200
    assert COST_FIELDS.issubset(response.context['adminform'].form.fields)


def test_task_admin_add_view_shows_costs_without_cost_permission(client, staff_user):
    add_permissions(staff_user, ['core.view_task', 'core.add_task'])
    client.force_login(staff_user)

    response = client.get(reverse('admin:core_task_add'))

    assert response.status_code == 200
    assert COST_FIELDS.issubset(response.context['adminform'].form.fields)


CLONED_COST_FIELDS = ('work_price', 'on_call_price', 'travel_price', 'overtime_price')


@pytest.mark.parametrize(
    ('permissions', 'expected_copied'),
    [
        pytest.param([], False, id='no-cost-permission'),
        pytest.param(['core.view_any_task_costs'], True, id='view-any-task-costs'),
        pytest.param(['core.manage_any_task_costs'], True, id='manage-any-task-costs'),
    ],
)
def test_task_admin_clone_copies_costs_only_with_cost_permission(client, staff_user, permissions, expected_copied):
    add_permissions(staff_user, ['core.view_task', 'core.change_task', 'core.add_task', *permissions])
    task = TaskFactory(contract=True, work_price=150, on_call_price=10, travel_price=20, overtime_price=30)
    client.force_login(staff_user)

    response = client.get(reverse('admin:core_task_clone', args=[task.pk]), follow=True)

    assert response.status_code == 200
    initial = response.context['adminform'].form.initial
    assert initial['title'] == task.title
    for field in CLONED_COST_FIELDS:
        assert (initial.get(field) == getattr(task, field)) is expected_copied, field
