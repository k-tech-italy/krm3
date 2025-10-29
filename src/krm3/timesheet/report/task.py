import datetime
from decimal import Decimal as D  # noqa: N817

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from krm3.core.models import Resource, Task
from krm3.timesheet.report.base import TimesheetReport
from krm3.timesheet.report.online import ReportBlock, ReportRow
from krm3.timesheet.rules import Krm3Day
from krm3.utils.numbers import normal

User = get_user_model()

task_timeentry_key_mapping = {
    'night_shift': _('Night shift'),
    'on_call': _('On call'),
    'travel': _('Travel'),
}


class TimesheetTaskReport(TimesheetReport):
    """Task-focused timesheet report that extends the base TimesheetReport."""

    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User) -> None:
        super().__init__(from_date, to_date, user)

        self.tasks: dict[int, list[Task]] = {}
        self._load_tasks()
        self._enrich_calendars_with_task_data()

    def _load_tasks(self) -> None:
        """Load tasks for all resources in the report."""
        resource_ids = [r.id for r in self.resources]

        tasks = Task.objects.filter(
            resource_id__in=resource_ids,
            start_date__lte=self.to_date
        ).filter(Q(end_date__gte=self.from_date) | Q(end_date__isnull=True))

        for task in tasks:
            self.tasks.setdefault(task.resource_id, []).append(task)

    def _enrich_calendars_with_task_data(self) -> None:
        """Add task hour data to existing calendar days."""
        for resource_id, calendar_days in self.calendars.items():
            resource_tasks = self.tasks.get(resource_id, [])

            for kd in calendar_days:
                self._calculate_task_hours_for_day(kd, resource_tasks, resource_id)

    def _calculate_task_hours_for_day(self, kd: Krm3Day, tasks: list[Task], resource_id: int) -> None:
        """Calculate task hours for a specific day."""
        day_entries = [
            te for te in self.time_entries
            if te.resource_id == resource_id and te.date == kd.date
        ]

        for task in tasks:
            task_hours = sum(
                (te.day_shift_hours or 0) +
                (te.night_shift_hours or 0) +
                (te.travel_hours or 0)
                for te in day_entries
                if te.task_id == task.id
            )
            if task_hours > 0:
                setattr(kd, f'task_{task.id}_hours', D(task_hours))


class TimesheetTaskReportOnline(TimesheetTaskReport):
    """Online HTML report for task-focused timesheets."""

    def report_html(self) -> list[ReportBlock]:
        blocks = []
        for resource in self.resources:
            blocks.append(block := ReportBlock(resource))
            row = block.add_row(ReportRow())
            resources_report_days = self.calendars[resource.id]

            num_giorni, tot_hh = self._calculate_summary_data(resources_report_days)

            row.add_cell(normal(num_giorni))
            row.add_cell(normal(tot_hh))

            for kd in resources_report_days:
                row.add_cell(kd)

            self._add_task_rows(block, resource)
            self._add_days_per_task_row(block, resource, resources_report_days)
            self._add_timeentry_type_rows(block, resources_report_days)
            self._add_absence_row(block, resource, resources_report_days)

        return blocks

    def _calculate_summary_data(self, resources_report_days: list[Krm3Day]) -> tuple[int, D]:
        """Calculate number of working days and total scheduled hours."""
        num_giorni = 0
        tot_hh = D(0)

        for kd in resources_report_days:
            if not kd.nwd:
                num_giorni += 1
                scheduled_hours = self._get_min_working_hours(kd)
                tot_hh += D(scheduled_hours)

        return num_giorni, tot_hh

    def _add_timeentry_type_rows(self, block: ReportBlock, resources_report_days: list[Krm3Day]) -> None:
        """Add rows for different time entry types (night shift, on call, travel)."""
        for key, label in task_timeentry_key_mapping.items():
            row = block.add_row(ReportRow())
            row.add_cell(label)

            entry_giorni = D(0)
            entry_total_hours = D(0)

            for kd in resources_report_days:
                if not kd.nwd:
                    value = getattr(kd, f'data_{key}', None)
                    if value and value > 0:
                        entry_total_hours += value
                        scheduled_hours = self._get_min_working_hours(kd)
                        if scheduled_hours > 0:
                            giorni_for_day = value / D(scheduled_hours)
                            entry_giorni += giorni_for_day

            row.add_cell(normal(entry_giorni))
            row.add_cell(normal(entry_total_hours))

            for rkd in resources_report_days:
                value = getattr(rkd, f'data_{key}', None)
                row.add_cell(normal(value) if value else '').nwd = rkd.nwd

    def _add_days_per_task_row(self, block: ReportBlock, resource: Resource,
                               resources_report_days: list[Krm3Day]) -> None:
        """Add a row showing total hours per day from all tasks."""
        resource_tasks = self.tasks.get(resource.id, [])
        daily_totals = self._calculate_daily_totals(resources_report_days, resource_tasks)

        row = ReportRow()
        row.add_cell(_("Total per day"))

        total_giorni = D(0)
        total_hours = sum(daily_totals.values())

        for kd in resources_report_days:
            if not kd.nwd:
                daily_total = daily_totals.get(kd.date, D(0))
                if daily_total > 0:
                    scheduled_hours = self._get_min_working_hours(kd)
                    if scheduled_hours > 0:
                        giorni_for_day = daily_total / D(scheduled_hours)
                        total_giorni += giorni_for_day

        row.add_cell(normal(total_giorni))
        row.add_cell(normal(total_hours))

        for kd in resources_report_days:
            daily_total = daily_totals.get(kd.date, D(0))
            row.add_cell(normal(daily_total) if daily_total > 0 else '').nwd = kd.nwd

        block.rows.append(row)

    def _calculate_daily_totals(self, resources_report_days: list[Krm3Day],
                                resource_tasks: list[Task]) -> dict:
        """Calculate daily totals for all tasks."""
        daily_totals = {}

        for kd in resources_report_days:
            daily_total = D(0)
            for task in resource_tasks:
                task_hours = getattr(kd, f'task_{task.id}_hours', None)
                if task_hours and task_hours > 0:
                    daily_total += task_hours
            daily_totals[kd.date] = daily_total

        return daily_totals

    def _add_task_rows(self, block: ReportBlock, resource: Resource) -> None:
        """Add rows for each task associated with the resource."""
        resources_report_days: list[Krm3Day] = self.calendars[resource.id]
        resource_tasks = self.tasks.get(resource.id, [])

        block.has_tasks = bool(resource_tasks)

        for task in resource_tasks:
            row = ReportRow()
            row.add_cell(task.title)

            task_giorni = D(0)
            task_total_hours = D(0)

            for kd in resources_report_days:
                task_hours = getattr(kd, f'task_{task.id}_hours', None)

                if task_hours and task_hours > 0:
                    task_total_hours += task_hours

                if not kd.nwd and task_hours and task_hours > 0:
                    scheduled_hours = self._get_min_working_hours(kd)
                    if scheduled_hours > 0:
                        giorni_for_day = task_hours / D(scheduled_hours)
                        task_giorni += giorni_for_day

            row.add_cell(normal(task_giorni))
            row.add_cell(normal(task_total_hours))

            for kd in resources_report_days:
                task_hours = getattr(kd, f'task_{task.id}_hours', None)
                row.add_cell(normal(task_hours) if task_hours else '').nwd = kd.nwd

            block.rows.append(row)

    def _add_absence_row(self, block: ReportBlock, resource: Resource,
                         resources_report_days: list[Krm3Day]) -> None:
        """Add a row showing absence markers with schedule-based calculation."""
        row = ReportRow()
        row.add_cell(_("Absences"))

        total_absence_giorni = D(0)
        total_absence_hours = D(0)

        for kd in resources_report_days:
            if not kd.nwd:
                absence_hours = self._calculate_absence_hours_for_day(kd)
                if absence_hours > 0:
                    total_absence_hours += absence_hours
                    scheduled_hours = self._get_min_working_hours(kd)
                    if scheduled_hours > 0:
                        giorni_for_day = absence_hours / D(scheduled_hours)
                        total_absence_giorni += giorni_for_day

        row.add_cell(normal(total_absence_giorni))
        row.add_cell(normal(total_absence_hours))

        for kd in resources_report_days:
            marker = self._get_absence_marker(kd)
            row.add_cell(marker).nwd = kd.nwd

        block.rows.append(row)

    def _calculate_absence_hours_for_day(self, kd: Krm3Day) -> D:
        """Calculate total absence hours for a single day."""
        absence_hours = D(0)

        if kd.data_holiday:
            absence_hours += kd.data_holiday
        if kd.data_sick:
            absence_hours += kd.data_sick
        if kd.data_leave:
            absence_hours += kd.data_leave
        if kd.data_special_leave_hours:
            absence_hours += kd.data_special_leave_hours

        return absence_hours

    def _get_absence_marker(self, kd: Krm3Day) -> str:
        """Get the appropriate absence marker for a day."""
        if kd.data_holiday:
            return 'F'
        if kd.data_sick:
            return 'M'
        if kd.data_leave or kd.data_special_leave_hours:
            return 'L'
        return ''
