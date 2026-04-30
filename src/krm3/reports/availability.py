import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, cast, override

import tablib
from django.utils.translation import gettext_lazy

from krm3.core.models.auth import Resource
from krm3.core.models.contracts import Contract, ContractQuerySet
from krm3.core.models.projects import Project
from krm3.core.models.timesheets import TimeEntry, TimeEntryQuerySet
from krm3.reports.generator import Period, ReportGenerator
from krm3.timesheet.rules import Krm3Day


class AbsenceKind(Enum):
    HOLIDAY = gettext_lazy('H')
    SICK = gettext_lazy('S')
    LEAVE = gettext_lazy('L')
    SPECIAL_LEAVE = gettext_lazy('SL')
    REST = gettext_lazy('R')


_ABSENCE_SHOW_HOURS = {AbsenceKind.LEAVE, AbsenceKind.SPECIAL_LEAVE, AbsenceKind.REST}


class Absence(NamedTuple):
    kind: AbsenceKind
    hours: Decimal

    def __str__(self) -> str:
        displayed_hours = self.hours if self.kind in _ABSENCE_SHOW_HOURS else ''
        return f'{self.kind.value} {displayed_hours}'.rstrip()


@dataclass
class AbsenceReportCell:
    date: datetime.date
    resource: Resource
    absences: list[Absence] = field(default_factory=list)

    def __str__(self) -> str:
        return ', '.join(str(absence) for absence in self.absences)

    def is_working_day(self) -> bool:
        contract = self.resource.get_contract_for_date(self.date)
        return contract is not None and Krm3Day(self.date).is_working_day(contract.country_calendar_code)


class AvailabilityReport(ReportGenerator):
    @override
    def __init__(self, period: Period, project: str | Project | None) -> None:
        start, end = period
        contracts = cast('ContractQuerySet', Contract.objects).active_between(start, end, including_end=True)
        resources = (
            Resource.objects.filter(id__in=contracts.values_list('resource_id').distinct())
            .order_by('last_name')
            .prefetch_related('task_set')
        )
        if isinstance(project, str):
            project = Project.objects.get(id=project)
        if project:
            resources = resources.filter(task__project=project)
        self.resources = resources.distinct()

        super().__init__(period, project)

    @override
    def collect(self, project: Project | None) -> TimeEntryQuerySet:
        return cast(
            'TimeEntryQuerySet',
            TimeEntry.objects.filter(
                date__gte=self.start, date__lt=self.end, resource__in=self.resources
            ).select_related('special_leave_reason'),
        )

    @override
    def process(self, time_entries: TimeEntryQuerySet) -> tablib.Dataset:
        entries_by_key: dict[tuple[int, datetime.date], list[TimeEntry]] = defaultdict(list)
        for entry in time_entries:
            entries_by_key[(entry.resource.id, entry.date)].append(entry)

        headers = ['Resource'] + [d.strftime('%a %d') for d in self.dates]
        dataset = tablib.Dataset(headers=headers)

        for resource in self.resources:
            row = [f'{resource.first_name} {resource.last_name}']
            for date in self.dates:
                entries = entries_by_key.get((resource.pk, date), [])
                absences = self._compute_absences(entries)
                row.append(AbsenceReportCell(date, resource, absences))  # pyright: ignore
            dataset.append(row)

        return dataset

    def _compute_absences(self, entries: list[TimeEntry]) -> list[Absence]:
        absences = []

        for entry in entries:
            if entry.holiday_hours > 0:
                absences.append(Absence(AbsenceKind.HOLIDAY, entry.holiday_hours))
                break
            if entry.sick_hours > 0:
                absences.append(Absence(AbsenceKind.SICK, entry.sick_hours))
                break
            if entry.leave_hours > 0:
                absences.append(Absence(AbsenceKind.LEAVE, entry.leave_hours))
            if entry.special_leave_hours > 0:
                absences.append(Absence(AbsenceKind.SPECIAL_LEAVE, entry.special_leave_hours))
            if entry.rest_hours > 0:
                absences.append(Absence(AbsenceKind.REST, entry.rest_hours))

        return absences
