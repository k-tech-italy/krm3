import datetime
import decimal
import json

from constance import config
from django.contrib.auth import get_user_model
from decimal import Decimal as D  # noqa: N817


from krm3.config import settings
from krm3.core.models import TimeEntry, Resource, Task, ExtraHoliday, Contract
from krm3.timesheet.report.online import ReportBlock, ReportRow, ReportCell
from krm3.timesheet.rules import Krm3Day

from krm3.utils.dates import KrmDay, get_country_holidays
from krm3.utils.numbers import normal

from django.db.models import Q

User = get_user_model()

task_timeentry_key_mapping = {
    'night_shift': 'Notturni',
    'on_call': 'Reperibilità',
    'travel': 'Ore Trasferta',
}

class TimesheetTaskReport:
    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User) -> None:
        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            self.resources = Resource.objects.filter(preferred_in_report=True)
        else:
            self.resources = [user.get_resource()]
        resource_ids = {r.id for r in self.resources}

        self.from_date = from_date
        self.to_date = to_date
        self.user = user

        self.default_schedule: dict[str, float] = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)
        top_period = to_date + datetime.timedelta(days=1) if to_date else None

        self.country_codes: set[str] = {settings.HOLIDAYS_CALENDAR}
        self.resource_contracts: dict[int, list[Contract]] = {}

        self.time_entries: list[TimeEntry] = TimeEntry.objects.filter(
            date__gte=self.from_date, date__lte=self.to_date, resource_id__in=resource_ids
        )

        for contract in list(
            Contract.objects.filter(period__overlap=(from_date, top_period), resource_id__in=resource_ids)
        ):
            self.resource_contracts.setdefault(contract.resource_id, []).append(contract)
            if contract.country_calendar_code and contract.country_calendar_code not in self.country_codes:
                self.country_codes.add(contract.country_calendar_code)

        resources_with_entries = {te.resource_id for te in self.time_entries}
        self.resources = [r for r in self.resources if r.id in resources_with_entries]

        self.tasks: dict[int, list[Task]] = {}
        self._load_tasks()

        self.extra_holidays = self._get_extra_holidays()
        self._holiday_cache = {}

        self.calendars: dict[int, list[Krm3Day]] = self._get_calendars()

    def _get_holiday(self, kd: 'KrmDay', country_calendar_code: str) -> bool:
        """Return True if the day is holiday."""
        if res := self._holiday_cache.get((kd.date, country_calendar_code)):
            return res
        if (eh := self.extra_holidays.get(kd)) and (
            country_calendar_code in eh or country_calendar_code.split('-')[0] in eh
        ):
            hol = True
        else:
            cal = get_country_holidays(country_calendar_code=country_calendar_code)
            hol = not cal.is_working_day(kd.date)
        return self._holiday_cache.setdefault((kd.date, country_calendar_code), hol)

    def _get_extra_holidays(self) -> dict[KrmDay, list[str]]:
        """Retrieve the extra holidays for the given country codes."""
        short_codes = {x.split('-')[0] for x in self.country_codes}
        result = {}
        extra_holidays = list(
            ExtraHoliday.objects.filter(
                country_codes__overlap=list(self.country_codes.union(short_codes)),
                period__overlap=(self.from_date, self.to_date),
            )
        )

        for eh in extra_holidays:
            for kd in KrmDay(eh.period.lower).range_to(eh.period.upper - datetime.timedelta(days=1)):
                result.setdefault(kd, []).extend(eh.country_codes)
        return result

    def _load_tasks(self) -> None:
        """Load tasks for all resources in the report."""
        resource_ids = {r.id for r in self.resources}

        for task in Task.objects.filter(
                resource_id__in=resource_ids,
                start_date__lte=self.to_date
        ).filter(Q(end_date__gte=self.from_date) | Q(end_date__isnull=True)):
            self.tasks.setdefault(task.resource_id, []).append(task)

    def _get_calendars(self) -> dict[int, list[Krm3Day]]:
        """Build calendars with task data."""
        ret: dict[int, list[Krm3Day]] = {}
        for resource in self.resources:
            res_id = resource.id
            contracts: list[Contract] = self.resource_contracts.get(res_id) or []

            ret[res_id] = list(Krm3Day(self.from_date, resource=resource).range_to(self.to_date))

            for kd in ret[res_id]:
                kd.resource = resource
                for c in contracts:
                    if c.falls_in(kd):
                        kd.contract = c
                        break

                country_calendar_code = (
                    kd.contract.country_calendar_code
                    if kd.contract and kd.contract.country_calendar_code
                    else settings.HOLIDAYS_CALENDAR
                )
                kd.holiday = self._get_holiday(kd, country_calendar_code)
                day_entries = [te for te in self.time_entries if te.resource_id == res_id and te.date == kd.date]
                kd.apply(day_entries)

                resource_tasks = self.tasks.get(res_id, [])
                for task in resource_tasks:
                    task_hours = sum(
                        (te.day_shift_hours or 0) +
                        (te.night_shift_hours or 0) +
                        (te.travel_hours or 0)
                        for te in day_entries
                        if te.task_id == task.id
                    )
                    if task_hours > 0:
                        setattr(kd, f'task_{task.id}_hours', D(task_hours))

        return ret

class TimesheetTaskReportOnline(TimesheetTaskReport):
    def report_html(self) -> list[ReportBlock]:
        blocks = []
        for resource in self.resources:
            blocks.append(block := ReportBlock(resource))
            row = block.add_row(ReportRow())
            resources_report_days = self.calendars[resource.id]
            row.add_cell(sum([0 if kd.nwd else 1 for kd in resources_report_days]))
            for kd in resources_report_days:
                row.add_cell(kd)

            if any(rkd.has_data for rkd in resources_report_days):
                self._add_task_rows(block, resource)

                for key, label in task_timeentry_key_mapping.items():
                    row = block.add_row(ReportRow())
                    row.add_cell(label)
                    row.add_cell(cell_tot_hh := ReportCell(decimal.Decimal(0)))
                    for rkd in resources_report_days:
                        value = getattr(rkd, f'data_{key}', None)
                        row.add_cell(normal(value)).nwd = rkd.nwd
                        cell_tot_hh.value += value or decimal.Decimal(0)
                    cell_tot_hh.value = normal(cell_tot_hh.value)

        return blocks

    def _add_task_rows(self, block: ReportBlock, resource: Resource) -> None:
        """Add rows for each task associated with the resource."""
        resources_report_days: list[Krm3Day] = self.calendars[block.resource.id]
        resource_tasks = self.tasks.get(resource.id, [])

        for task in resource_tasks:
            row = ReportRow()
            row.add_cell(task.title)
            row.add_cell(cell_tot_hh := ReportCell(decimal.Decimal(0)))
            for rkd in resources_report_days:
                value = getattr(rkd, f'task_{task.id}_hours', None)
                row.add_cell(normal(value) if value else '').nwd = rkd.nwd
                cell_tot_hh.value += value or decimal.Decimal(0)
            cell_tot_hh.value = normal(cell_tot_hh.value)
            block.rows.append(row)
