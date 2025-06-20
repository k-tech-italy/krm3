"""Non-model domain data-transfer-objects for the timesheet."""

import datetime
from typing import Self

from krm3.core.models.auth import Resource, User
from krm3.core.models.projects import Task, TaskQuerySet
from krm3.core.models.timesheets import TimeEntry, TimeEntryQuerySet
from krm3.utils.dates import KrmCalendar


class TimesheetDTO:
    def __init__(self, requested_by: User) -> None:
        self.tasks = TaskQuerySet().none()
        self.time_entries = TimeEntryQuerySet().none()
        self._requested_by = requested_by
        self.resource = None
    def fetch(self, resource: Resource, start_date: datetime.date, end_date: datetime.date) -> Self:
        self.tasks = (
            Task.objects.filter_acl(self._requested_by)  # pyright: ignore[reportAttributeAccessIssue]
            .active_between(start_date, end_date)
            .assigned_to(resource=resource)
        )
        self.time_entries = TimeEntry.objects.filter_acl(self._requested_by).filter(  # pyright: ignore[reportAttributeAccessIssue]
            resource=resource, date__range=(start_date, end_date)
        )
        calendar = KrmCalendar()

        self.days = calendar.iter_dates(start_date, end_date)
        self.resource = resource

        return self
