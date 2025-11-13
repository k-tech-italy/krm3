import datetime
from decimal import Decimal as D  # noqa: N817

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from krm3.core.models import Project, Resource
from krm3.timesheet.report.base import TimesheetReport
from krm3.timesheet.report.online import ReportBlock, ReportRow
from krm3.timesheet.rules import Krm3Day

User = get_user_model()


class AvailabilityReport(TimesheetReport):
    def __init__(
        self, from_date: datetime.date, to_date: datetime.date, user: User, project: str | None = None
    ) -> None:
        self.project = Project.objects.get(id=project) if project else None
        super().__init__(from_date, to_date, user)
        self._enrich_calendars_with_availability_data()

    def _set_resources(self, user: User, **kwargs) -> None:
        """Set the resource list.

        Will filter for resources with contracts overlapping current period and eventually by project.
        """
        qs = Resource.objects.prefetch_related('contract_set').filter(
            contract__period__overlap=(self.from_date, self.to_date + relativedelta(days=1))
        )
        if self.project is not None:
            qs = qs.prefetch_related('task_set').filter(task__project=self.project)

        self.resources = list(qs.distinct())

    def _enrich_calendars_with_availability_data(self) -> None:
        """Add availability/absence data to existing calendar days."""
        for resource_id, calendar_days in self.calendars.items():
            for kd in calendar_days:
                self._calculate_availability_for_day(kd, resource_id)

    def _calculate_availability_for_day(self, kd: Krm3Day, resource_id: int) -> None:
        """Calculate availability status for a specific day."""
        day_entries = [te for te in self.time_entries if te.resource_id == resource_id and te.date == kd.date]

        for te in day_entries:
            if te.holiday_hours and te.holiday_hours > 0:
                kd.absence_type = 'H'
                kd.absence_hours = D(te.holiday_hours)
                break
            if (te.leave_hours and te.leave_hours > 0) or (te.special_leave_hours and te.special_leave_hours > 0):
                kd.absence_type = 'L'
                total_leave = (te.leave_hours or 0) + (te.special_leave_hours or 0)
                kd.absence_hours = D(total_leave)
                break
        else:
            kd.absence_type = None
            kd.absence_hours = D(0)


class AvailabilityReportOnline(AvailabilityReport):
    """Online HTML report for availability/absences."""

    need = {'extra_holidays'}

    def report_html(self) -> list[ReportBlock]:
        """Return a single ReportBlock containing all resources in one table."""
        if not self.resources:
            return []

        block = ReportBlock(None)

        calendar_days = self.calendars[self.resources[0].id]

        days_row = ReportRow()
        days_row.add_cell(_('Days'))
        for kd in calendar_days:
            days_row.add_cell(f'{kd.day_of_week_short_i18n}\n{kd.date.day}')
        block.rows.append(days_row)

        for resource in self.resources:
            resource_row = ReportRow()
            resource_name = f'{resource.first_name} {resource.last_name}'
            resource_row.add_cell(resource_name)

            resource_days = self.calendars[resource.id]
            for kd in resource_days:
                if hasattr(kd, 'absence_type') and kd.absence_type:
                    if kd.absence_type == 'H':
                        cell_value = 'H'
                    elif kd.absence_type == 'L':
                        if hasattr(kd, 'absence_hours') and kd.absence_hours > 0:
                            cell_value = f'L {kd.absence_hours}'
                        else:
                            cell_value = 'L'
                else:
                    cell_value = ''

                cell = resource_row.add_cell(cell_value)
                cell.nwd = kd.nwd

            block.rows.append(resource_row)

        return [block]
