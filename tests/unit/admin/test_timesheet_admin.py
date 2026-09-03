from datetime import timedelta

from django.test import RequestFactory
from testutils.factories import DayEntryFactory, TaskEntryFactory, TimesheetSubmissionFactory

from krm3.timesheet.admin import DayEntryAdmin, TaskEntryAdmin


def test_admin_cannot_change_or_delete_entries_in_closed_submission(admin_user):
    day_entry = DayEntryFactory()
    task_entry = TaskEntryFactory(day_entry=day_entry, resource=day_entry.resource)
    TimesheetSubmissionFactory(
        resource=day_entry.resource,
        period=(day_entry.day, day_entry.day + timedelta(days=1)),
        closed=True,
    )
    day_entry.refresh_from_db()
    task_entry.refresh_from_db()

    request = RequestFactory().get('/')
    request.user = admin_user
    day_entry_admin = DayEntryAdmin(model=day_entry.__class__, admin_site=None)
    task_entry_admin = TaskEntryAdmin(model=task_entry.__class__, admin_site=None)

    assert day_entry_admin.has_change_permission(request, day_entry) is False
    assert day_entry_admin.has_delete_permission(request, day_entry) is False
    assert task_entry_admin.has_change_permission(request, task_entry) is False
    assert task_entry_admin.has_delete_permission(request, task_entry) is False
