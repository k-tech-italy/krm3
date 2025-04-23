import pytest
from django.contrib.auth.models import Permission

from factories import TimeEntryFactory, ResourceFactory, TaskFactory


@pytest.mark.parametrize(
    'user, perm, expected',  # noqa: PT006
    [
        pytest.param('admin', None, 'all', id='admin-all'),
        pytest.param('regular', None, 'own', id='user-own'),
        pytest.param('regular', 'view_any_timesheet', 'all', id='permitted-viewer'),
        pytest.param('regular', 'manage_any_timesheet', 'all', id='permitted-manager'),
    ],
)
def test_user_can_manage_own_timesheets(user, perm, expected, admin_user, regular_user):
    user_time_entry = TimeEntryFactory(resource=ResourceFactory(user=regular_user), task=TaskFactory())
    admin_time_entry = TimeEntryFactory(resource=ResourceFactory(user=admin_user), task=TaskFactory())
    user = admin_user if user == 'admin' else regular_user
    if perm:
        user.user_permissions.add(Permission.objects.get(codename=perm))

    from krm3.core.models import TimeEntry

    entries = set(TimeEntry.objects.filter_acl(user=user).all())
    assert entries == {user_time_entry, admin_time_entry} if expected == 'all' else {user_time_entry}


@pytest.mark.parametrize(
    'user, perm, expected',  # noqa: PT006
    [
        pytest.param('admin', None, 'all', id='admin-all'),
        pytest.param('regular', None, 'own', id='user-own'),
        pytest.param('regular', 'view_any_project', 'all', id='permitted-viewer'),
        pytest.param('regular', 'manage_any_project', 'all', id='permitted-manager'),
    ],
)
def test_user_can_access_own_tasks(user, perm, expected, admin_user, regular_user):
    user_task = TaskFactory(resource=ResourceFactory(user=regular_user))
    admin_task = TaskFactory(resource=ResourceFactory(user=admin_user))
    user = admin_user if user == 'admin' else regular_user
    if perm:
        user.user_permissions.add(Permission.objects.get(codename=perm))

    from krm3.core.models import Task

    entries = set(Task.objects.filter_acl(user=user).all())
    assert entries == {user_task, admin_task} if expected == 'all' else {user_task}
