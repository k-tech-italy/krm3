"""Non-model domain data-transfer-objects for the timesheet."""

import datetime
from typing import Self

from krm3.core.models.auth import Resource, User
from krm3.core.models.projects import Task, TaskQuerySet
from krm3.core.models.timesheets import TimeEntry, TimeEntryQuerySet
from krm3.utils.dates import KrmCalendar
from constance import config

class TimesheetDTO:
    def __init__(self, requested_by: User) -> None:
        self.tasks = TaskQuerySet().none()
        self.time_entries = TimeEntryQuerySet().none()
        self._requested_by = requested_by
        self.resource = None
        self.schedule = {}
        self.timesheet_colors = {}
        self.bank_hours = 0.0

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

        self.schedule = resource.get_schedule(start_date, end_date)

        self.timesheet_colors['less_than_schedule_color_bright_theme'] = config.LESS_THAN_SCHEDULE_COLOR_BRIGHT_THEME
        self.timesheet_colors['exact_schedule_color_bright_theme'] = config.EXACT_SCHEDULE_COLOR_BRIGHT_THEME
        self.timesheet_colors['more_than_schedule_color_bright_theme'] = config.MORE_THAN_SCHEDULE_COLOR_BRIGHT_THEME
        self.timesheet_colors['less_than_schedule_color_dark_theme'] = config.LESS_THAN_SCHEDULE_COLOR_DARK_THEME
        self.timesheet_colors['exact_schedule_color_dark_theme'] = config.EXACT_SCHEDULE_COLOR_DARK_THEME
        self.timesheet_colors['more_than_schedule_color_dark_theme'] = config.MORE_THAN_SCHEDULE_COLOR_DARK_THEME

        self.bank_hours = resource.get_bank_hours_balance()

        return self
