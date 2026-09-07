"""Non-model domain data-transfer-objects for the timesheet."""

import datetime
import typing
from typing import Self, cast

from constance import config
from django.contrib.postgres.fields import ranges
from ktcalendars import KTDay
from psycopg.types.range import DateRange

from krm3.core.models.auth import Resource, User
from krm3.core.models.contracts import Contract
from krm3.core.models.projects import Task, TaskQuerySet
from krm3.core.models.timesheets import DayEntriesQuerySet, DayEntry

if typing.TYPE_CHECKING:
    from krm3.config.fragments.constance import ConstanceTyping


class TimesheetDTO:
    def __init__(self, requested_by: User | None = None) -> None:
        self.tasks = TaskQuerySet().none()
        self.day_entries = DayEntriesQuerySet().none()
        self.requested_by = requested_by
        self.resource = None
        self.schedule = {}
        self.timesheet_colors = {}
        self.bank_hours = 0.0
        self.days = []
        self.contracts = Contract.objects.none()

    def fetch(self, resource: Resource, start_date: datetime.date, end_date: datetime.date) -> Self:
        """Fetch the resource timesheet for a specific date interval."""
        task_qs = Task.objects.filter_acl(self.requested_by) if self.requested_by else Task.objects.all()
        self.tasks = cast(
            'TaskQuerySet',
            (task_qs.filter(period__overlap=DateRange(start_date, end_date))),
        ).assigned_to(resource=resource)

        te_qs = DayEntry.objects.filter_acl(self.requested_by) if self.requested_by else DayEntry.objects.all()
        self.day_entries = te_qs.filter(resource=resource, day__range=(start_date, end_date))

        self.contracts = Contract.objects.filter(
            resource=resource,
            period__overlap=ranges.DateRange(start_date, end_date + datetime.timedelta(days=1)),
        )

        self.resource = resource

        contract_map = resource.get_contract_map(start_date, end_date)
        for period, contract in sorted(contract_map.items()):
            for day in period:
                if contract is None:
                    self.days.append(KTDay(day))
                    self.schedule[day] = 0.0
                else:
                    self.days.append(contract.get_ktday(day))
                    self.schedule[day] = float(contract.get_due_hours(day))

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

        self.bank_hours = resource.get_bank_hours_balance(end_date)

        return self
