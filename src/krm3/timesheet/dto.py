"""Non-model domain data-transfer-objects for the timesheet."""

import datetime
import typing
from typing import Self

from constance import config
from django.contrib.postgres.fields import ranges

from krm3.core.models.auth import Resource, User
from krm3.core.models.contracts import Contract
from krm3.core.models.projects import Task, TaskQuerySet
from krm3.core.models.timesheets import TimeEntry, TimeEntryQuerySet
from krm3.utils.dates import KrmCalendar

if typing.TYPE_CHECKING:
    from krm3.config.fragments.constance import ConstanceTyping


class TimesheetDTO:
    def __init__(self, requested_by: User | None = None) -> None:
        self.tasks = TaskQuerySet().none()
        self.time_entries = TimeEntryQuerySet().none()
        self._requested_by = requested_by
        self.resource = None
        self.schedule = {}
        self.timesheet_colors = {}
        self.bank_hours = 0.0
        self.contracts = Contract.objects.none()

    def fetch(self, resource: Resource, start_date: datetime.date, end_date: datetime.date) -> Self:
        """Fetch the resource timesheet for a specific date interval."""
        task_qs = Task.objects.filter_acl(self._requested_by) if self._requested_by else Task.objects.all()
        self.tasks = task_qs.active_between(start_date, end_date).assigned_to(resource=resource)
        te_qs = TimeEntry.objects.filter_acl(self._requested_by) if self._requested_by else TimeEntry.objects.all()
        self.time_entries = te_qs.filter(resource=resource, date__range=(start_date, end_date))

        self.contracts = Contract.objects.filter(
            resource=resource, period__overlap=ranges.DateRange(start_date, end_date)
        )

        calendar = KrmCalendar()

        self.days = calendar.iter_dates(start_date, end_date)
        self.resource = resource

        self.schedule = resource.get_schedule(start_date, end_date)

        conf: ConstanceTyping = config
        self.timesheet_colors.update(
            {
                'less_than_schedule_color_bright_theme': conf.LESS_THAN_SCHEDULE_COLOR_BRIGHT_THEME,
                'exact_schedule_color_bright_theme': conf.EXACT_SCHEDULE_COLOR_BRIGHT_THEME,
                'more_than_schedule_color_bright_theme': conf.MORE_THAN_SCHEDULE_COLOR_BRIGHT_THEME,
                'less_than_schedule_color_dark_theme': conf.LESS_THAN_SCHEDULE_COLOR_DARK_THEME,
                'exact_schedule_color_dark_theme': conf.EXACT_SCHEDULE_COLOR_DARK_THEME,
                'more_than_schedule_color_dark_theme': conf.MORE_THAN_SCHEDULE_COLOR_DARK_THEME,
            }
        )

        self.bank_hours = resource.get_bank_hours_balance()

        return self
