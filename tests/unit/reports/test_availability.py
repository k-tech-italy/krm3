import datetime
from decimal import Decimal

import pytest
from testutils.factories import (
    ContractFactory,
    ProjectFactory,
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

    def test_dataset_row_headers_contain_all_resources(self):
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

    def test_resource_with_no_entries_has_no_absences(self):
        resource = ResourceFactory()
        ContractFactory(resource=resource)

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        ).processed_data

        row = dataset[0]
        cell = row[1]
        assert cell.absences == []

    def test_project_filters_resources(self):
        project = ProjectFactory()
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        ContractFactory(resource=resource1)
        ContractFactory(resource=resource2)
        task1 = TaskFactory(resource=resource1, project=project)
        task2 = TaskFactory(resource=resource2)
        TimeEntryFactory(
            resource=resource1,
            date=datetime.date(2025, 8, 1),
            task=task1,
            day_shift_hours=8,
        )
        TimeEntryFactory(
            resource=resource2,
            date=datetime.date(2025, 8, 1),
            task=task2,
            day_shift_hours=8,
        )

        dataset_with_project = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=project,
        ).processed_data

        dataset_without_project = AvailabilityReport(
            period=(datetime.date(2025, 8, 1), datetime.date(2025, 8, 2)),
            project=None,
        ).processed_data

        assert len(dataset_with_project) == 1
        assert resource1.full_name in dataset_with_project['Resource']
        assert len(dataset_without_project) == 2

    def test_dataset_with_various_entries_across_multiple_days_and_resources(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        resource1 = ResourceFactory()
        resource2 = ResourceFactory()
        ContractFactory(resource=resource1)
        ContractFactory(resource=resource2)
        task1 = TaskFactory(resource=resource1, project=project_a)
        task2 = TaskFactory(resource=resource2, project=project_b)

        TimeEntryFactory(
            resource=resource1,
            date=datetime.date(2025, 8, 4),
            task=None,
            day_shift_hours=0,
            holiday_hours=8,
        )
        TimeEntryFactory(
            resource=resource1,
            date=datetime.date(2025, 8, 5),
            task=None,
            day_shift_hours=0,
            leave_hours=3,
            special_leave_hours=2,
            rest_hours=1,
            special_leave_reason=SpecialLeaveReasonFactory(),
        )
        TimeEntryFactory(
            resource=resource1,
            date=datetime.date(2025, 8, 6),
            task=None,
            day_shift_hours=0,
            leave_hours=4,
        )
        TimeEntryFactory(
            resource=resource1,
            date=datetime.date(2025, 8, 7),
            task=task1,
            day_shift_hours=8,
        )

        TimeEntryFactory(
            resource=resource2,
            date=datetime.date(2025, 8, 4),
            task=task2,
            day_shift_hours=8,
        )
        TimeEntryFactory(
            resource=resource2,
            date=datetime.date(2025, 8, 5),
            task=None,
            day_shift_hours=0,
            sick_hours=8,
        )
        TimeEntryFactory(
            resource=resource2,
            date=datetime.date(2025, 8, 6),
            task=None,
            day_shift_hours=0,
            leave_hours=4,
        )

        dataset = AvailabilityReport(
            period=(datetime.date(2025, 8, 4), datetime.date(2025, 8, 8)),
            project=None,
        ).processed_data

        dataset_project_a = AvailabilityReport(
            period=(datetime.date(2025, 8, 4), datetime.date(2025, 8, 8)),
            project=project_a,
        ).processed_data

        dataset_project_b = AvailabilityReport(
            period=(datetime.date(2025, 8, 4), datetime.date(2025, 8, 8)),
            project=project_b,
        ).processed_data

        assert len(dataset) == 2
        assert len(dataset_project_a) == 1
        assert len(dataset_project_b) == 1
        assert resource1.full_name in dataset['Resource']
        assert resource2.full_name in dataset['Resource']
        assert resource1.full_name in dataset_project_a['Resource']
        assert resource2.full_name not in dataset_project_a['Resource']
        assert resource2.full_name in dataset_project_b['Resource']
        assert resource1.full_name not in dataset_project_b['Resource']

        r1_row = dataset[0] if dataset[0][0] == resource1.full_name else dataset[1]
        r2_row = dataset[1] if dataset[1][0] == resource2.full_name else dataset[0]

        assert r1_row[1].absences == [Absence(AbsenceKind.HOLIDAY, Decimal(8))]
        assert r1_row[2].absences == [
            Absence(AbsenceKind.LEAVE, Decimal(3)),
            Absence(AbsenceKind.SPECIAL_LEAVE, Decimal(2)),
            Absence(AbsenceKind.REST, Decimal(1)),
        ]
        assert r1_row[3].absences == [Absence(AbsenceKind.LEAVE, Decimal(4))]
        assert r1_row[4].absences == []

        assert r2_row[1].absences == []
        assert r2_row[2].absences == [Absence(AbsenceKind.SICK, Decimal(8))]
        assert r2_row[3].absences == [Absence(AbsenceKind.LEAVE, Decimal(4))]
        assert r2_row[4].absences == []
