import datetime
from decimal import Decimal

import pytest
from django.utils.translation import gettext as _

from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ProjectFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
)

from krm3.core.models import DayEntry, Resource
from krm3.reports.availability import Absence, AbsenceKind, AbsenceReportCell, AvailabilityReport
from krm3.reports.generator import ReportGenerator

AUGUST = (_dt('2025-08-01'), _dt('2025-09-01'))


def _days() -> list[datetime.date]:
    current = _dt('2025-08-01')
    end = _dt('2025-09-01')
    days = []
    while current < end:
        days.append(current)
        current += datetime.timedelta(days=1)
    return days


def _day_headers() -> list[str]:
    return [f'{_(d.strftime("%a"))}\n{d.day}' for d in _days()]


def _report_row(dataset, resource) -> dict:
    for row in dataset.dict:
        if row['Days'] == f'{resource.first_name} {resource.last_name}':
            return row
    raise AssertionError(f'resource {resource} not found in report')


def _cell_for(report, resource, day) -> AbsenceReportCell:
    row = _report_row(report.processed_data, resource)
    cells = [cell for key, cell in row.items() if key != 'Days']
    return dict(zip(_days(), cells, strict=True))[day]


def _entry(**kwargs) -> DayEntry:
    entry = DayEntry()
    for key, value in kwargs.items():
        setattr(entry, key, value)
    return entry


class TestAbsenceFromDayEntry:
    def test_none(self):
        assert Absence.from_day_entry(None) == []

    def test_empty_entry(self):
        assert Absence.from_day_entry(_entry()) == []

    def test_asked_holiday(self):
        assert Absence.from_day_entry(_entry(asked_holiday=True)) == [Absence(AbsenceKind.HOLIDAY)]

    def test_calendar_holiday(self):
        assert Absence.from_day_entry(_entry(is_holiday=True)) == [Absence(AbsenceKind.HOLIDAY)]

    def test_sick(self):
        assert Absence.from_day_entry(_entry(is_sick=True)) == [Absence(AbsenceKind.SICK)]

    def test_leave(self):
        assert Absence.from_day_entry(_entry(leave_hours=Decimal('3.00'))) == [
            Absence(AbsenceKind.LEAVE, Decimal('3.00')),
        ]

    def test_special_leave(self):
        assert Absence.from_day_entry(_entry(special_leave_hours=Decimal('2.00'))) == [
            Absence(AbsenceKind.SPECIAL_LEAVE, Decimal('2.00')),
        ]

    def test_rest(self):
        assert Absence.from_day_entry(_entry(rest_hours=Decimal('1.00'))) == [
            Absence(AbsenceKind.REST, Decimal('1.00')),
        ]

    def test_multiple_absences(self):
        entry = _entry(
            leave_hours=Decimal('3.00'),
            special_leave_hours=Decimal('2.00'),
            rest_hours=Decimal('1.00'),
        )
        assert Absence.from_day_entry(entry) == [
            Absence(AbsenceKind.LEAVE, Decimal('3.00')),
            Absence(AbsenceKind.SPECIAL_LEAVE, Decimal('2.00')),
            Absence(AbsenceKind.REST, Decimal('1.00')),
        ]


class TestAbsenceStr:
    def test_holiday_shows_no_hours(self):
        assert str(Absence(AbsenceKind.HOLIDAY)) == 'H'

    def test_sick_shows_no_hours(self):
        assert str(Absence(AbsenceKind.SICK)) == 'S'

    def test_leave_shows_hours(self):
        assert str(Absence(AbsenceKind.LEAVE, Decimal('3.00'))) == 'L 3.00'

    def test_special_leave_shows_hours(self):
        assert str(Absence(AbsenceKind.SPECIAL_LEAVE, Decimal('3.00'))) == 'SL 3.00'

    def test_rest_shows_hours(self):
        assert str(Absence(AbsenceKind.REST, Decimal('5.00'))) == 'R 5.00'


class TestAbsenceKindShowHours:
    def test_marker_kinds_do_not_show_hours(self):
        assert AbsenceKind.HOLIDAY.show_hours is False
        assert AbsenceKind.SICK.show_hours is False

    def test_hour_kinds_show_hours(self):
        assert AbsenceKind.LEAVE.show_hours is True
        assert AbsenceKind.SPECIAL_LEAVE.show_hours is True
        assert AbsenceKind.REST.show_hours is True


class TestAbsenceReportCellStr:
    def test_no_absences(self):
        cell = AbsenceReportCell(date=_dt('2025-08-01'), resource=Resource(), absences=[])
        assert str(cell) == ''

    def test_multiple_absences(self):
        cell = AbsenceReportCell(
            date=_dt('2025-08-01'),
            resource=Resource(),
            absences=[
                Absence(AbsenceKind.LEAVE, Decimal('3.00')),
                Absence(AbsenceKind.SPECIAL_LEAVE, Decimal('2.00')),
            ],
        )
        assert str(cell) == 'L 3.00, SL 2.00'


@pytest.mark.django_db
def test_instantiation_returns_tablib_dataset():
    ContractFactory(resource=ResourceFactory())
    report = AvailabilityReport(AUGUST, None)
    assert isinstance(report, ReportGenerator)
    assert report.processed_data is not None


@pytest.mark.django_db
def test_header_row_contains_only_period_days():
    ContractFactory(resource=ResourceFactory())
    report = AvailabilityReport(AUGUST, None)
    headers = list(report.processed_data.headers)
    assert headers[0] == 'Days'
    assert headers[1:] == _day_headers()
    assert len(headers) - 1 == 31


@pytest.mark.django_db
def test_one_row_per_resource():
    r1 = ResourceFactory()
    r2 = ResourceFactory()
    ContractFactory(resource=r1)
    ContractFactory(resource=r2)
    report = AvailabilityReport(AUGUST, None)
    names = {row['Days'] for row in report.processed_data.dict}
    assert names == {f'{r1.first_name} {r1.last_name}', f'{r2.first_name} {r2.last_name}'}


@pytest.mark.django_db
def test_holiday_asked_holiday_sick_leave_special_leave_rest():
    days = _days()
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=AUGUST)

    DayEntryFactory(resource=resource, contract=contract, day=days[0], asked_holiday=True)
    DayEntryFactory(resource=resource, contract=contract, day=days[1], is_sick=True)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=days[2],
        leave_hours=3,
        special_leave_hours=3,
        special_leave_reason=SpecialLeaveReasonFactory(),
    )
    DayEntryFactory(resource=resource, contract=contract, day=days[3], rest_hours=5)
    DayEntryFactory(resource=resource, contract=contract, day=days[4])

    report = AvailabilityReport(AUGUST, None)
    row = _report_row(report.processed_data, resource)
    cells = [cell for key, cell in row.items() if key != 'Days']
    by_day = dict(zip(_day_headers(), cells, strict=True))
    assert str(by_day[_day_headers()[0]]) == 'H'
    assert str(by_day[_day_headers()[1]]) == 'S'
    assert str(by_day[_day_headers()[2]]) == 'L 3.00, SL 3.00'
    assert str(by_day[_day_headers()[3]]) == 'R 5.00'
    assert str(by_day[_day_headers()[4]]) == ''


@pytest.mark.django_db
def test_no_contract_day_is_blank():
    days = _days()
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(days[0], days[2]))

    report = AvailabilityReport(AUGUST, None)
    row = _report_row(report.processed_data, resource)
    cells = [cell for key, cell in row.items() if key != 'Days']
    assert str(cells[0]) == ''
    assert str(cells[1]) == ''


@pytest.mark.django_db
def test_project_filter_by_object_and_pk():
    project = ProjectFactory()
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=AUGUST)
    TaskFactory(project=project, resource=resource, period=AUGUST)
    other = ResourceFactory()
    ContractFactory(resource=other, period=AUGUST)

    report = AvailabilityReport(AUGUST, project)
    names = {row['Days'] for row in report.processed_data.dict}
    assert names == {f'{resource.first_name} {resource.last_name}'}

    report_by_pk = AvailabilityReport(AUGUST, str(project.pk))
    names = {row['Days'] for row in report_by_pk.processed_data.dict}
    assert names == {f'{resource.first_name} {resource.last_name}'}


@pytest.mark.django_db
def test_empty_period_returns_headers_only():
    report = AvailabilityReport(AUGUST, None)
    assert list(report.processed_data.headers)[0] == 'Days'
    assert report.processed_data.height == 0


class TestAbsenceReportCellIsWorkingDay:
    def test_defaults_to_working_day(self):
        cell = AbsenceReportCell(date=_dt('2025-08-04'), resource=Resource(), absences=[])
        assert cell.is_workday is True

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ('day', 'contract_period', 'entry_kwargs', 'expected'),
        [
            pytest.param(_dt('2025-08-04'), AUGUST, {'due_hours': 3}, True, id='entry-normal-working-day'),
            pytest.param(_dt('2025-08-04'), AUGUST, {'is_holiday': True}, False, id='entry-marked-holiday'),
            pytest.param(_dt('2025-08-04'), AUGUST, {}, False, id='entry-zero-due-hours'),
            pytest.param(_dt('2025-08-04'), AUGUST, None, True, id='no-entry-monday-working-day'),
            pytest.param(_dt('2025-08-09'), AUGUST, None, False, id='no-entry-saturday-weekend'),
            pytest.param(_dt('2025-08-15'), AUGUST, None, False, id='no-entry-ferragosto-holiday'),
            pytest.param(
                _dt('2025-08-20'),
                (_dt('2025-08-01'), _dt('2025-08-15')),
                None,
                False,
                id='no-entry-after-contract-end',
            ),
            pytest.param(
                _dt('2025-08-01'),
                (_dt('2025-08-15'), _dt('2025-09-01')),
                None,
                False,
                id='no-entry-before-contract-start',
            ),
        ],
    )
    def test_is_working_day(self, day, contract_period, entry_kwargs, expected):
        resource = ResourceFactory()
        contract = ContractFactory(resource=resource, period=contract_period)
        if entry_kwargs is not None:
            DayEntryFactory(resource=resource, contract=contract, day=day, **entry_kwargs)
        report = AvailabilityReport(AUGUST, None)
        assert _cell_for(report, resource, day).is_workday is expected
