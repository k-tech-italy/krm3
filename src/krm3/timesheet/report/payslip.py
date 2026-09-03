from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from ktcalendars import KTDateRange, KTDay

from krm3.core.models import Contract, DayEntry, Resource
from krm3.utils import i18n
from krm3.utils.numbers import normal

from .online import ReportBlock, ReportCell, ReportRow
from .queries import resources_in_period

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from django.db.models import QuerySet
    from ktcalendars.types import KTDayType

    from krm3.core.models import User

    class PreparedResource(Resource):
        contract_set: Any
        dayentry_set: Any

    class NwdReportCell(ReportCell):
        nwd: bool


REPORT_FIELDS: tuple[tuple[str, Any], ...] = (
    ('bank', _('Bank hours')),
    ('due_hours', _('Due hours')),
    ('regular_hours', _('Regular hours')),
    ('day_hours', _('Day shift hours')),
    ('night_hours', _('Night shift hours')),
    ('on_call_hours', _('On call')),
    ('travel_hours', _('Travel')),
    ('holiday_hours', _('Holiday')),
    ('leave_hours', _('Leave')),
    ('rest_hours', _('Rest')),
    ('overtime_hours', _('Overtime')),
    ('meal_voucher', _('Meal voucher')),
)


@dataclass
class TimesheetReportDay:
    day: KTDay
    entry: DayEntry | None
    persisted: bool = False

    @property
    def date(self) -> datetime.date:
        return self.day.date

    @property
    def day_of_week_short_i18n(self) -> str:
        return i18n.short_day_of_week(self.date)

    @property
    def holiday(self) -> bool:
        return bool(self.entry and self.entry.is_holiday)

    @property
    def nwd(self) -> bool:
        return self.entry is None or self.entry.nwd

    @property
    def submitted(self) -> bool:
        return bool(self.entry and self.entry.closed)

    def value(self, field_name: str) -> Decimal | int:
        if self.entry is None:
            return Decimal(0)
        if field_name == 'holiday_hours':
            return self.entry.due_hours if self.entry.asked_holiday else Decimal(0)
        return getattr(self.entry, field_name)


@dataclass
class ResourceTimesheetReportData:
    resource: Resource
    days: list[TimesheetReportDay]

    @property
    def has_data(self) -> bool:
        return any(day.persisted for day in self.days)


@dataclass
class TimesheetReportData:
    """Dataclass containing all informations that will be rendered in a report."""

    start_date: KTDayType
    end_date: KTDayType
    period: KTDateRange = field(init=False)
    days: list[KTDay] = field(init=False)
    resources: list[ResourceTimesheetReportData] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.period = KTDateRange.from_start_end(self.start_date, self.end_date)
        self.days = list(self.period)


class TimesheetReport:
    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User, **kwargs: Any) -> None:
        self.report_data = TimesheetReportData(from_date, to_date)
        resources = resources_in_period(
            start_date=from_date,
            end_date=to_date,
            tasks=False,
            project_id=None,
        ).order_by('last_name', 'first_name')
        contracts = Contract.objects.filter(period__overlap=self.report_data.period).order_by('period')

        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            resources = resources.filter(
                contract__period__overlap=self.report_data.period,
                contract__contract_type=Contract.ContractType.EMPLOYEE,
            ).distinct()
        else:
            resources = resources.filter(user=user)

        resources = resources.prefetch_related(
            Prefetch('contract_set', queryset=contracts),
            'dayentry_set__special_leave_reason',
        )
        self._prepare_data(resources)

    def _prepare_data(self, resources: QuerySet[Resource]) -> None:
        for resource in resources:
            resource = cast('PreparedResource', resource)
            entries_by_day: dict[datetime.date, DayEntry] = {}
            for entry in resource.dayentry_set.all():
                if entry.day in entries_by_day:
                    raise ValueError(f'Duplicate DayEntry for resource {resource.pk} on {entry.day}')
                entries_by_day[entry.day] = entry

            report_days = []
            for day in self.report_data.days:
                if entry := entries_by_day.get(day.date):
                    report_days.append(TimesheetReportDay(day, entry, persisted=True))
                    continue

                contract = next((contract for contract in resource.contract_set.all() if day in contract.period), None)
                report_days.append(TimesheetReportDay(day, self._placeholder(resource, contract, day)))

            self.report_data.resources.append(ResourceTimesheetReportData(resource, report_days))

    @staticmethod
    def _placeholder(resource: Resource, contract: Contract | None, day: KTDay) -> DayEntry | None:
        if contract is None:
            return None
        contract_day = contract.get_ktday(day)
        if contract_day is None:
            raise ValueError(f'Day {day.date} is outside Contract {contract.pk}')
        return DayEntry(
            day=day.date,
            resource=resource,
            contract=contract,
            due_hours=contract.get_due_hours(day),
            is_holiday=contract_day.is_holiday,
        )


class TimesheetReportOnline(TimesheetReport):
    def report_html(self) -> list[ReportBlock]:
        return [self._resource_block(resource_data) for resource_data in self.report_data.resources]

    def _resource_block(self, resource_data: ResourceTimesheetReportData) -> ReportBlock:
        block = ReportBlock(resource_data.resource)
        self._add_header(block, resource_data.days)
        if resource_data.has_data:
            self._add_timesheet_rows(block, resource_data.days)
        return block

    @staticmethod
    def _add_header(block: ReportBlock, days: list[TimesheetReportDay]) -> None:
        header = block.add_row(ReportRow())
        header.add_cell(sum(not day.nwd for day in days))
        for day in days:
            header.add_cell(day)

    def _add_timesheet_rows(self, block: ReportBlock, days: list[TimesheetReportDay]) -> None:
        for field_name, label in REPORT_FIELDS:
            self._add_row(block, days, label, (day.value(field_name) for day in days))
            if field_name == 'leave_hours':
                self._add_special_leave_rows(block, days)
                self._add_sick_rows(block, days)

    def _add_special_leave_rows(self, block: ReportBlock, days: list[TimesheetReportDay]) -> None:
        reasons = sorted(
            {
                day.entry.special_leave_reason.title
                for day in days
                if day.entry and day.entry.special_leave_hours and day.entry.special_leave_reason
            }
        )
        for reason in reasons:
            self._add_row(
                block,
                days,
                _('Special leave ({title})').format(title=reason),
                (
                    day.entry.special_leave_hours
                    if day.entry and day.entry.special_leave_reason and day.entry.special_leave_reason.title == reason
                    else Decimal(0)
                    for day in days
                ),
            )

    def _add_sick_rows(self, block: ReportBlock, days: list[TimesheetReportDay]) -> None:
        protocols = sorted({day.entry.protocol_number or '' for day in days if day.entry and day.entry.is_sick})
        if not protocols:
            protocols = ['']

        for protocol in protocols:
            label = _('Sick {title}').format(title=protocol) if protocol else _('Sick')
            self._add_row(
                block,
                days,
                label,
                (
                    day.entry.due_hours
                    if day.entry and day.entry.is_sick and (day.entry.protocol_number or '') == protocol
                    else Decimal(0)
                    for day in days
                ),
            )

    @staticmethod
    def _add_row(
        block: ReportBlock,
        days: list[TimesheetReportDay],
        label: Any,
        values: Iterable[Decimal | int],
    ) -> None:
        row = block.add_row(ReportRow())
        row.add_cell(label)
        total_cell = row.add_cell(ReportCell(Decimal(0)))
        total = Decimal(0)

        for day, value in zip(days, values, strict=True):
            cell = cast('NwdReportCell', row.add_cell(normal(value) if value else None))
            cell.nwd = day.nwd
            total += Decimal(value)

        total_cell.value = normal(total)
