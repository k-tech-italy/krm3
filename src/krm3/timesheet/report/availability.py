import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import F, Func, Prefetch, QuerySet, Value
from django.utils.translation import gettext_lazy as _

from krm3.core.models import DayEntry, Resource, TaskEntry
from krm3.timesheet.report.online import ReportBlock, ReportRow
from ktcalendars.types import KTDayType
from krm3.utils.context_managers import SqlPerfMonitor
from ktcalendars import KTDateRange, KTDay

User = get_user_model()


class AbsenceType(Enum):
    HOLIDAY = _('H')
    SICK = _('S')
    LEAVE = _('L')
    SPECIAL_LEAVE = _('SL')
    REST = _('R')


ABSENCE_SHOW_HOURS = {AbsenceType.LEAVE, AbsenceType.SPECIAL_LEAVE, AbsenceType.REST}


def resources_in_period(
    start_date: datetime.date,
    end_date: datetime.date | None,
    tasks: bool,
    project_id: int | None,
) -> QuerySet[Resource]:
    """
    Fetch resources with contracts between two dates.

      Usage:

          for resource in resources_in_period(datetime.date(2026, 7, 1), datetime.date(2026, 7, 31)):
              for de in resource.dayentry_set.all():        # only entries in the period, no extra query
                  for te in de.taskentry_set.all():         # prefetched, .task also loaded

    Notes:
      - Open-ended period: passing (start_date, None) to period__overlap builds an unbounded-upper Postgres range,
        so it matches any contract that ends after start_date — that's your "end_date means max_date" case.
        The DayEntry filter correspondingly just drops the day__lte clause.
      - + timedelta(days=1): this follows the convention already used in this codebase
        (TimesheetSubmission.get_closed_in_period at src/krm3/core/models/timesheets.py:115) — an inclusive user-facing
         end date against the exclusive range upper bound. If your end_date is already exclusive, drop the shift.
      - distinct() is needed because a resource with two consecutive contracts both overlapping the period would
        otherwise appear twice.
      - select_related('task') on the task-entry prefetch avoids one query per task when you touch te.task; add more
        (e.g. 'task__project') if you need them.
      - When project_id is not None then task is forced True, and select_related('task') becomes
        select_related('task', 'project'). Additionally Resources are filtered for only those who have a Task in the
        period.

      One caveat: the day-entry prefetch is filtered by date only, not by "belongs to an overlapping contract" — if a
        resource has day entries in the period outside any contract you care about, add
        .filter(contract__period__overlap=period) to the day_entries queryset too.

    """
    # Contract.period upper bound is exclusive ("day after the actual end date"),
    # so an inclusive end_date must be shifted by one day; None upper = unbounded.
    period = KTDateRange.from_start_end(start_date, end_date)

    day_entries = DayEntry.objects.filter(day__contained_by=period)
    if tasks or project_id:
        filters = {}
        if project_id:
            filters = {'task__project_id': project_id, 'task__period__overlap': period}
        return (
            Resource.objects.filter(contract__period__overlap=period, **filters)
            .annotate(
                _contract_range=Func(
                    F('contract__period'),
                    Value(KTDateRange.from_start_end(start_date, end_date)),
                    function='',
                    template='%(expressions)s',
                )
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    'dayentry_set',
                    queryset=day_entries.order_by('day').prefetch_related(
                        Prefetch('taskentry_set', queryset=TaskEntry.objects.select_related('task'))
                    ),
                )
            )
        )

    return (
        Resource.objects.filter(contract__period__overlap=period)
        .distinct()
        .prefetch_related(Prefetch('dayentry_set', queryset=day_entries.order_by('day')))
    )


@dataclass
class AvailabilityReportDC:
    start_date: KTDayType
    end_date: KTDayType
    period: KTDateRange = field(init=False)
    days: list[KTDay] = field(init=False)
    tasks: list[TaskEntry] = field(default_factory=list)
    resources: dict[int, Resource] = field(default_factory=dict)
    extra_holidays: dict[str, KTDateRange] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialise period and days."""
        self.start_date = KTDay(self.start_date)
        self.end_date = KTDay(self.end_date)
        self.period = KTDateRange.from_start_end(start_date=self.start_date, end_date=self.end_date)
        self.days = list(self.period)


class AvailabilityReport:
    """The report will show all resources active in the date interval in one table.

    A resource is available if he/she has a contract and:
    - he/she is not sick
    - he/she did not ask holidays
    - he/she is not due to be on holiday given his/her calendar (fallback to default calendar)
    """

    def __init__(
        self,
        from_date: datetime.date,
        to_date: datetime.date,
        user: User,  # TODO: check if we need user
        project_id: int | None = None,
    ) -> None:
        self.report_data = AvailabilityReportDC(start_date=from_date, end_date=to_date)

        with SqlPerfMonitor(connection) as ctx:  # noqa: F841
            qs = resources_in_period(start_date=from_date, end_date=to_date, tasks=False, project_id=project_id)
            self._prepare_data(qs)

    def _prepare_data(self, qs: QuerySet) -> None:
        """Load the report data from the Queryset.

        For each resource we will have a dict[KTDay: DayEntry] where DayEntry if calculated as as follows (in order):
        1. The recorded DayEntry for the day if it exists
        2. An unbounded DayEntry associated to the contract if there is a contract for the day
        3. None
        """
        for resource in qs:
            self.report_data.resources.setdefault(resource.id, {'report_day_entries': {}, 'resource': resource})
            report_day_entries = self.report_data.resources[resource.id]['report_day_entries']

            # For each resource we prepare the list of Day
            resource_contracts = list(resource.contract_set.all())
            for rc in resource_contracts:
                report_day_entries.update(
                    {
                        day: DayEntry(day=day, resource=resource, contract=rc)
                        for day in KTDateRange(rc.period).intersection(self.report_data.period)
                    }
                )
            report_day_entries.update({KTDay(de.day): de for de in resource.dayentry_set.all()})
            self.report_data.resources[resource.id]['report_day_entries'] = {
                krm_day: report_day_entries.get(krm_day, None) for krm_day in self.report_data.days
            }


class AvailabilityReportOnline(AvailabilityReport):
    """Online HTML report for availability/absences."""

    def report_html(self) -> list[ReportBlock]:
        """Return a single ReportBlock containing all resources in one table."""
        if not self.report_data:
            return []

        block = ReportBlock(None)

        days_row = ReportRow()
        days_row.add_cell(_('Days'))
        for kd in self.report_data.days:
            days_row.add_cell(f'{_(kd.day_of_week_short)}\n{kd.date.day}')
        block.rows.append(days_row)

        for res in self.report_data.resources.values():
            resource, day_entries = res['resource'], res['report_day_entries']
            resource_row = ReportRow()
            resource_name = f'{resource.first_name} {resource.last_name}'
            resource_row.add_cell(resource_name)

            de: DayEntry
            for de in day_entries.values():
                cell_value = self.fx_cell_value(de)
                cell = resource_row.add_cell(cell_value)
                cell.nwd = de is not None and (de.is_holiday or de.contract is None)

            block.rows.append(resource_row)

        return [block]

    def fx_cell_value(self, de: DayEntry) -> list[Any]:
        cell_value = []

        if de:
            if de.is_holiday or de.asked_holiday:
                cell_value = [_('H')]
            elif de.is_sick:
                cell_value = [_('S')]
            else:
                if de.leave_hours:
                    cell_value.append(f"{_('L')} {de.leave_hours}")
                if de.special_leave_hours:
                    cell_value.append(f"{_('SL')} {de.special_leave_hours}")
                if de.rest_hours:
                    cell_value.append(f"{_('R')} {de.rest_hours}")

            cell_value = ', '.join(map(str, cell_value))
        return cell_value
