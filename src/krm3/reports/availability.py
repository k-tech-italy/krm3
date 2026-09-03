import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, Self, cast, override

import tablib
from django.utils.translation import gettext_lazy as _
from ktcalendars import KTCalendar, KTDay

from krm3.core.models import Contract, DayEntry, Project, Resource, ResourceQuerySet
from krm3.reports.generator import Period, ReportGenerator
from krm3.timesheet.report.queries import resources_in_period


type WorkdayMapping = dict[tuple[datetime.date, str], bool]


class AbsenceKind(Enum):
    """The kind of absence displayed in a report cell."""

    HOLIDAY = _('H')
    SICK = _('S')
    LEAVE = _('L')
    SPECIAL_LEAVE = _('SL')
    REST = _('R')

    @property
    def show_hours(self) -> bool:
        """Return True if the absence kind is rendered with its hours."""
        return self in {AbsenceKind.LEAVE, AbsenceKind.SPECIAL_LEAVE, AbsenceKind.REST}


class Absence(NamedTuple):
    """A single absence occurrence: a marker kind, plus hours where applicable."""

    kind: AbsenceKind
    hours: Decimal = Decimal(0)

    @classmethod
    def from_day_entry(cls, entry: DayEntry | None) -> list[Self]:
        """Build the absences described by a DayEntry (or none for a missing entry)."""
        if entry is None:
            return []
        if entry.is_holiday or entry.asked_holiday:
            return [cls(AbsenceKind.HOLIDAY)]
        if entry.is_sick:
            return [cls(AbsenceKind.SICK)]
        absences = []
        if entry.leave_hours:
            absences.append(cls(AbsenceKind.LEAVE, entry.leave_hours))
        if entry.special_leave_hours:
            absences.append(cls(AbsenceKind.SPECIAL_LEAVE, entry.special_leave_hours))
        if entry.rest_hours:
            absences.append(cls(AbsenceKind.REST, entry.rest_hours))
        return absences

    def __str__(self) -> str:
        shown_hours = self.hours if self.kind.show_hours else ''
        return f'{self.kind.value} {shown_hours}'.rstrip()


@dataclass(frozen=True)
class AbsenceReportCell:
    """Ad-hoc data structure retaining only the absence data for one day cell."""

    date: datetime.date
    resource: Resource
    absences: list[Absence] = field(default_factory=list)
    is_workday: bool = True

    def __str__(self) -> str:
        return ', '.join(str(absence) for absence in self.absences)


class AvailabilityReport(ReportGenerator[ResourceQuerySet, tablib.Dataset, [int | None]]):
    """The availability report generator.

    Shows all resources active in the period in a single table: one row per
    resource and one column per day. A resource is available on a given day
    if they have a contract covering it and is not sick, did not ask for
    holidays, and is not due to be on holiday given their calendar.
    """

    @override
    def __init__(self, period: Period, project: str | Project | None) -> None:
        self._workday_cache: WorkdayMapping = {}
        if project is not None and not isinstance(project, Project):
            project = Project.objects.get(pk=project)
        super().__init__(period, project.pk if project else None)

    @override
    def _collect(self, project_id: int | None) -> ResourceQuerySet:
        resources = resources_in_period(
            start_date=self.period_start,
            end_date=self.period_end - datetime.timedelta(days=1),
            tasks=False,
            project_id=project_id,
        ).prefetch_related('contract_set')

        calendars: dict[str, KTCalendar] = {}
        for resource in resources:
            for contract in resource.contract_set.all():
                if (code := contract.calendar_code) not in calendars:
                    calendars[code] = KTCalendar(country_code=code)
                    self._workday_cache |= {
                        (day, code): KTDay(day, ktcalendar=calendars[code]).is_workday for day in self.dates()
                    }

        return cast('ResourceQuerySet', resources)

    @override
    def _process(self, resources: ResourceQuerySet) -> tablib.Dataset:
        days = list(self.dates())

        dataset = tablib.Dataset()
        dataset.headers = [_('Days'), *[self._day_header(day) for day in days]]

        for resource in resources:
            contracts = list(resource.contract_set.all())
            contract_by_day = {
                day: contract for contract in contracts for day in days if self._contract_covers(contract, day)
            }
            entries = {entry.day: entry for entry in resource.dayentry_set.all()}
            dataset.append(
                [
                    resource.full_name,
                    *[
                        AbsenceReportCell(
                            date=day,
                            resource=resource,
                            absences=Absence.from_day_entry(entries.get(day)),
                            is_workday=self._is_workday(day, entries.get(day), contract_by_day.get(day)),
                        )
                        for day in days
                    ],
                ]
            )

        return dataset

    def _is_workday(
        self,
        day: datetime.date,
        entry: DayEntry | None,
        contract: Contract | None,
    ) -> bool:
        """Return True if the resource is expected to work on the given day.

        Prefers the day-entry data when available and falls back to the
        contract calendar for days without a recorded entry.
        """
        if entry is not None:
            return entry.is_workday
        if contract is not None:
            return self._workday_cache[(day, contract.calendar_code)]
        return False

    def _contract_covers(self, contract: Contract, day: datetime.date) -> bool:
        """Return True if the contract period covers the day (lower inclusive, upper exclusive)."""
        lower = contract.period.lower
        upper = contract.period.upper
        return (lower is None or day >= lower) and (upper is None or day < upper)

    def _day_header(self, day: datetime.date) -> str:
        return f'{_(day.strftime("%a"))}\n{day.day}'
