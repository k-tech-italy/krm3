import datetime
from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING, override

import openpyxl
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from ktcalendars import KTDateRange
from openpyxl.utils import get_column_letter

from krm3.core.models import Resource, Task
from krm3.timesheet.report.base import TimesheetReport
from krm3.timesheet.report.online import ReportBlock, ReportRow
from krm3.timesheet.rules import Krm3Day
from krm3.utils.numbers import normal
from krm3.web.report_styles import centered, header_alignment, header_fill, header_font, nwd_fill, thin_border

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

User = get_user_model()


def _excel_value(value: object) -> object:
    """Return the value to store in a spreadsheet cell: numbers as numbers, the rest as text."""
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value))
    except ArithmeticError:
        return str(value)
    return int(number) if number == number.to_integral_value() else float(number)

task_timeentry_key_mapping = {
    'night_shift': _('Night shift'),
    'on_call': _('On call'),
    'travel': _('Travel'),
}


class TimesheetTaskReport(TimesheetReport):
    """Task-focused timesheet report that extends the base TimesheetReport."""

    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User, **kwargs) -> None:
        can_filter_all = user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet')
        self.project_id = kwargs.get('project') if can_filter_all else None
        self.resource_id = kwargs.get('resource') if can_filter_all else None
        self.task_title = kwargs.get('task_title') if can_filter_all else None
        super().__init__(from_date, to_date, user, **kwargs)

        self.tasks: dict[int, list[Task]] = {}
        self._load_tasks()
        if self.project_id or self.task_title:
            self.resources = [r for r in self.resources if r.id in self.tasks]
        self._enrich_calendars_with_task_data()

    @override
    def _get_resources(self, user: User, **kwargs) -> Iterable[Resource]:
        """Fetch the resources for this report.

        Uses the base class to respect permissions, then optionally filters by resource_id.
        """
        resources = super()._get_resources(user)

        if self.resource_id:
            return [r for r in resources if r.pk == self.resource_id]

        return resources

    def _load_tasks(self) -> None:
        """Load tasks for all resources in the report."""
        resource_ids = [r.id for r in self.resources]

        tasks = Task.objects.filter(
            resource_id__in=resource_ids,
            period__overlap=KTDateRange.from_start_end(self.from_date, self.to_date),
        )
        if self.project_id:
            tasks = tasks.filter(project_id=self.project_id)
        if self.task_title:
            tasks = tasks.filter(title=self.task_title)

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
            te
            for te in self.task_entries
            if te.day_entry.resource_id == resource_id and te.day_entry.day == kd.date
        ]

        for task in tasks:
            task_hours = sum(
                (te.day_shift_hours or 0) + (te.night_shift_hours or 0) + (te.travel_hours or 0)
                for te in day_entries
                if te.task_id == task.id
            )
            if task_hours > 0:
                setattr(kd, f'task_{task.id}_hours', Decimal(task_hours))


class TimesheetTaskReportOnline(TimesheetTaskReport):
    """Online HTML report for task-focused timesheets."""

    need = {'extra_holidays'}

    def report_html(self, tasks_only: bool = False) -> list[ReportBlock]:
        blocks = []
        for resource in self.resources:
            blocks.append(block := ReportBlock(resource))
            row = block.add_row(ReportRow())
            resources_report_days = self.calendars[resource.id]

            scheduled_working_days, scheduled_working_hours = self._calculate_summary_data(resources_report_days)

            row.add_cell(normal(scheduled_working_days))
            row.add_cell(normal(scheduled_working_hours))

            for kd in resources_report_days:
                row.add_cell(kd)

            self._add_task_rows(block, resource)
            self._add_days_per_task_row(block, resource, resources_report_days)
            self._add_timeentry_type_rows(block, resources_report_days, resource)
            if not tasks_only:
                self._add_absence_row(block, resources_report_days)

        return blocks

    def write_excel(self, stream: 'SupportsWrite[bytes]', title: str, tasks_only: bool = False) -> None:
        """Write the report as an XLSX workbook laid out like the online page.

        Each resource gets a header row (name, scheduled days and hours, one column per day) followed by its rows;
        non-working days are shaded and numbers are written as numbers.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 14

        current_row = 1
        for block in self.report_html(tasks_only=tasks_only):
            header_row, *rows = block.rows
            days, hours, *day_cells = header_row.cells
            headers = [
                f'{block.resource.last_name} {block.resource.first_name}',
                f'{_("Days")} {days.render()}',
                f'{_("Total HH")} {hours.render()}',
                *(f'{cell.value.day_of_week_short_i18n}\n{cell.value.date.day}' for cell in day_cells),
            ]
            for col, value in enumerate(headers, 1):
                cell = ws.cell(row=current_row, column=col, value=value)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = thin_border
                cell.alignment = header_alignment
            # room for the two-line day headers
            ws.row_dimensions[current_row].height = 30
            for col, day_cell in enumerate(day_cells, 4):
                ws.column_dimensions[get_column_letter(col)].width = 6
                if day_cell.value.nwd:
                    ws.cell(row=current_row, column=col).fill = nwd_fill
            current_row += 1

            if not block.has_tasks:
                ws.cell(row=current_row, column=1, value=str(_('No tasks assigned'))).border = thin_border
                current_row += 1
            else:
                for row in rows:
                    for col, report_cell in enumerate(row.cells, 1):
                        cell = ws.cell(row=current_row, column=col, value=_excel_value(report_cell.value))
                        cell.border = thin_border
                        if col > 1:
                            cell.alignment = centered
                        if getattr(report_cell, 'nwd', False):
                            cell.fill = nwd_fill
                    current_row += 1

            # spacing between resources
            current_row += 1

        wb.save(stream)

    def _calculate_summary_data(self, resources_report_days: list[Krm3Day]) -> tuple[int, Decimal]:
        """Calculate number of working days and total scheduled hours."""
        scheduled_working_days = 0
        scheduled_working_hours = Decimal(0)

        for kd in resources_report_days:
            if not kd.nwd:
                scheduled_working_days += 1
                scheduled_hours = self._get_min_working_hours(kd)
                scheduled_working_hours += Decimal(scheduled_hours)

        return scheduled_working_days, scheduled_working_hours

    def _add_timeentry_type_rows(
        self, block: ReportBlock, resources_report_days: list[Krm3Day], resource: Resource
    ) -> None:
        """Add rows for different time entry types (night shift, on call, travel)."""
        resource_task_ids = {t.id for t in self.tasks.get(resource.id, [])}

        for key, label in task_timeentry_key_mapping.items():
            row = block.add_row(ReportRow())
            row.add_cell(label)

            entry_days = Decimal(0)
            entry_total_hours = Decimal(0)

            for kd in resources_report_days:
                if key in ('night_shift', 'travel'):
                    day_entries = [
                        te
                        for te in self.task_entries
                        if te.day_entry.resource_id == resource.id
                        and te.day_entry.day == kd.date
                        and te.task_id in resource_task_ids
                    ]
                    value = Decimal(sum(getattr(te, f'{key}_hours', 0) or 0 for te in day_entries))
                else:
                    value = getattr(kd, f'data_{key}', None) or Decimal(0)

                if not kd.nwd and value and value > 0:
                    entry_total_hours += value
                    scheduled_hours = self._get_min_working_hours(kd)
                    if scheduled_hours > 0:
                        hours_ratio = value / Decimal(scheduled_hours)
                        entry_days += hours_ratio

            row.add_cell(normal(entry_days))
            row.add_cell(normal(entry_total_hours))

            for rkd in resources_report_days:
                if key in ('night_shift', 'travel'):
                    day_entries = [
                        te
                        for te in self.task_entries
                        if te.day_entry.resource_id == resource.id
                        and te.day_entry.day == rkd.date
                        and te.task_id in resource_task_ids
                    ]
                    value = Decimal(sum(getattr(te, f'{key}_hours', 0) or 0 for te in day_entries))
                else:
                    value = getattr(rkd, f'data_{key}', None) or Decimal(0)
                row.add_cell(normal(value) if value else '').nwd = rkd.nwd

    def _add_days_per_task_row(
        self, block: ReportBlock, resource: Resource, resources_report_days: list[Krm3Day]
    ) -> None:
        """Add a row showing total hours per day from all tasks."""
        resource_tasks = self.tasks.get(resource.id, [])
        daily_totals = self._calculate_daily_totals(resources_report_days, resource_tasks)

        row = ReportRow()
        row.add_cell(_('Total per day'))

        total_days = Decimal(0)
        total_hours = sum(daily_totals.values())

        for day in resources_report_days:
            if not day.nwd:
                daily_total = daily_totals.get(day.date, Decimal(0))
                if daily_total > 0:
                    scheduled_hours = self._get_min_working_hours(day)
                    if scheduled_hours > 0:
                        hours_ratio = daily_total / Decimal(scheduled_hours)
                        total_days += hours_ratio

        row.add_cell(normal(total_days))
        row.add_cell(normal(total_hours))

        for day in resources_report_days:
            daily_total = daily_totals.get(day.date, Decimal(0))
            row.add_cell(normal(daily_total) if daily_total > 0 else '').nwd = day.nwd

        block.rows.append(row)

    def _calculate_daily_totals(self, resources_report_days: list[Krm3Day], resource_tasks: list[Task]) -> dict:
        """Calculate daily totals for all tasks."""
        daily_totals = {}

        for day in resources_report_days:
            daily_total = Decimal(0)
            for task in resource_tasks:
                task_hours = getattr(day, f'task_{task.id}_hours', None)
                if task_hours and task_hours > 0:
                    daily_total += task_hours
            daily_totals[day.date] = daily_total

        return daily_totals

    def _add_task_rows(self, block: ReportBlock, resource: Resource) -> None:
        """Add rows for each task associated with the resource."""
        resources_report_days: list[Krm3Day] = self.calendars[resource.id]
        resource_tasks = self.tasks.get(resource.id, [])

        # FIXME: this is a pure function of the current state, use a property
        block.has_tasks = bool(resource_tasks)

        for task in resource_tasks:
            row = ReportRow()
            row.add_cell(task)

            total_days = Decimal(0)
            total_hours = Decimal(0)

            for day in resources_report_days:
                task_hours = getattr(day, f'task_{task.id}_hours', None)

                if task_hours and task_hours > 0:
                    total_hours += task_hours

                if not day.nwd and task_hours and task_hours > 0:
                    scheduled_hours = self._get_min_working_hours(day)
                    if scheduled_hours > 0:
                        hours_ratio = task_hours / Decimal(scheduled_hours)
                        total_days += hours_ratio

            row.add_cell(normal(total_days))
            row.add_cell(normal(total_hours))

            for day in resources_report_days:
                task_hours = getattr(day, f'task_{task.id}_hours', None)
                row.add_cell(normal(task_hours) if task_hours else '').nwd = day.nwd

            block.rows.append(row)

    def _add_absence_row(self, block: ReportBlock, resources_report_days: list[Krm3Day]) -> None:
        """Add a row showing absence markers with schedule-based calculation."""
        row = ReportRow()
        row.add_cell(_('Absences'))

        total_absence_days = Decimal(0)
        total_absence_hours = Decimal(0)

        for day in resources_report_days:
            if not day.nwd:
                absence_hours = self._calculate_absence_hours_for_day(day)
                if absence_hours > 0:
                    total_absence_hours += absence_hours
                    scheduled_hours = self._get_min_working_hours(day)
                    if scheduled_hours > 0:
                        hours_ratio = absence_hours / Decimal(scheduled_hours)
                        total_absence_days += hours_ratio

        row.add_cell(normal(total_absence_days))
        row.add_cell(normal(total_absence_hours))

        for day in resources_report_days:
            marker = self._get_absence_marker(day)
            row.add_cell(marker).nwd = day.nwd

        block.rows.append(row)

    def _calculate_absence_hours_for_day(self, kd: Krm3Day) -> Decimal:
        """Calculate total absence hours for a single day."""
        absence_hours = Decimal(0)

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
