import datetime
from decimal import Decimal

import pytest
from testutils.factories import (
    ContractFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TimeEntryFactory,
)

from krm3.reports.availability import Absence, AbsenceKind, AvailabilityReport


@pytest.mark.django_db
class TestComputeAbsences:
    """Unit tests for _compute_absences method."""

    def test_holiday(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            holiday_hours=8,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [(AbsenceKind.HOLIDAY, entry.holiday_hours)]

    def test_sick(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            sick_hours=8,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [(AbsenceKind.SICK, entry.sick_hours)]

    def test_leave(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            leave_hours=3,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [(AbsenceKind.LEAVE, entry.leave_hours)]

    def test_special_leave(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            special_leave_hours=2,
            special_leave_reason=SpecialLeaveReasonFactory(),
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [(AbsenceKind.SPECIAL_LEAVE, entry.special_leave_hours)]

    def test_rest(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            rest_hours=1,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [(AbsenceKind.REST, entry.rest_hours)]

    def test_leaves_and_rest_in_one_entry(self):
        entry = TimeEntryFactory(
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            leave_hours=3,
            special_leave_hours=2,
            special_leave_reason=SpecialLeaveReasonFactory(),
            rest_hours=1,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == [
            (AbsenceKind.LEAVE, entry.leave_hours),
            (AbsenceKind.SPECIAL_LEAVE, entry.special_leave_hours),
            (AbsenceKind.REST, entry.rest_hours),
        ]

    def test_no_absences(self):
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([])
        assert result == []

    def test_day_shift_hours_does_not_create_absences(self):
        resource = ResourceFactory()
        task = TaskFactory(resource=resource)
        entry = TimeEntryFactory(
            resource=resource,
            date=datetime.date(2025, 8, 1),
            task=task,
            day_shift_hours=8,
        )
        report = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        )
        result = report._compute_absences([entry])
        assert result == []


@pytest.mark.django_db
class TestProcess:
    """Unit tests for process method and dataset generation."""

    def test_dataset_headers(self):
        resource = ResourceFactory()
        ContractFactory(resource=resource)

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 4)),
            project=None,
        ).processed_data

        assert dataset.headers[0] == 'Resource'
        assert len(dataset.headers) == 4
        assert 'Fri 01' in dataset.headers
        assert 'Sat 02' in dataset.headers
        assert 'Sun 03' in dataset.headers

    def test_dataset_row_count_matches_resources(self):
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        ContractFactory(resource=resource1)
        ContractFactory(resource=resource2)

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        ).processed_data

        assert len(dataset) == 2
        assert set(dataset['Resource']) == {resource1.full_name, resource2.full_name}

    def test_dataset_cell_collects_absence_data(self):
        resource = ResourceFactory()
        ContractFactory(resource=resource)
        TimeEntryFactory(
            resource=resource,
            date=datetime.date(2025, 8, 1),
            day_shift_hours=0,
            holiday_hours=8,
        )

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        ).processed_data

        row = dataset[0]
        cell = row[1]
        assert cell.date == datetime.date(2025, 8, 1)
        assert cell.resource == resource
        assert cell.absences == [Absence(AbsenceKind.HOLIDAY, Decimal(8))]

    def test_resource_with_no_entries_has_empty_lists(self):
        resource = ResourceFactory()
        ContractFactory(resource=resource)

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        ).processed_data

        row = dataset[0]
        cell = row[1]
        assert cell.absences == []
