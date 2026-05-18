"""Non-model domain data-transfer-objects for the timesheet."""

import datetime
import typing
from typing import Self

from constance import config
from django.contrib.postgres.fields import ranges

from krm3.core.models.auth import Resource, User
from krm3.core.models.contracts import Contract
from krm3.core.models.projects import Task, TaskQuerySet
from krm3.core.models.timesheets import TaskEntry, TaskEntriesQuerySet, DayEntry, DayEntriesQuerySet
from krm3.utils.dates import KrmCalendar
from dateutil.relativedelta import relativedelta

if typing.TYPE_CHECKING:
    from krm3.config.fragments.constance import ConstanceTyping


class TimesheetDTO:
    def __init__(self, requested_by: User | None = None) -> None:
        self.tasks = TaskQuerySet().none()
        self.day_entries = DayEntriesQuerySet().none()
        self.requested_by = requested_by
        self.resource = None
        self.timesheet_colors = {}
        self.bank_hours = 0.0
        self.contracts = Contract.objects.none()

    def fetch(self, resource: Resource, start_date: datetime.date, end_date: datetime.date) -> Self:
        """Fetch the resource timesheet for a specific date interval."""
        upper = end_date + relativedelta(days=1)
        self.tasks = Task.objects.filter(period__overlap=(start_date, upper)).assigned_to(
            resource=resource
        )
        if self.requested_by:
            self.tasks = self.tasks.filter_acl(user=self.requested_by)

        self.day_entries = DayEntry.objects.filter(
            day__gte=start_date, day__lte=end_date
        ).prefetch_related('taskentry_set').select_related('contract')
        if self.requested_by:
            self.day_entries = self.day_entries.filter_acl(user=self.requested_by)

        self.contracts = Contract.objects.filter(
            resource=resource, period__overlap=ranges.DateRange(start_date, upper)
        )
        if self.requested_by:
            self.contracts = self.contracts.filter_acl(user=self.requested_by)

        self.days = list(KrmCalendar().iter_dates(start_date, end_date))
        self.resource = resource

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

        self.bank_hours = resource.get_bank_hours_balance(at=end_date)

        return self
