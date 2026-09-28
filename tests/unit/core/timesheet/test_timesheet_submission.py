from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskEntryFactory,
    TaskFactory,
    TimesheetSubmissionFactory,
)

from krm3.timesheet.rules import Krm3Day


def test_submission_state_is_synchronized_with_day_entries():
    resource = ResourceFactory()
    day_entry = DayEntryFactory(resource=resource, day=date(2024, 1, 3))
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-01-08'),
        closed=True,
    )

    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is True

    submission.closed = False
    submission.save()
    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is False

    submission.closed = True
    submission.save()
    submission.delete()
    day_entry.refresh_from_db()
    assert day_entry.timesheet is None
    assert day_entry.closed is False


def test_closed_entries_cannot_be_deleted_until_submission_is_reopened():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2024, 1, 1), date(2024, 2, 1)))
    task = TaskFactory(resource=resource, period=contract.period)
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    task_entry = TaskEntryFactory(day_entry=day_entry, task=task)
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-02-01'),
        closed=True,
    )

    day_entry.refresh_from_db()
    task_entry.refresh_from_db()

    with pytest.raises(ValidationError, match='Closed time entries cannot be deleted'):
        day_entry.delete()
    with pytest.raises(ValidationError, match='Closed time entries cannot be deleted'):
        task_entry.delete()
    with pytest.raises(ValidationError, match='Closed time entries cannot be deleted'):
        day_entry.__class__.objects.filter(pk=day_entry.pk).delete()
    with pytest.raises(ValidationError, match='Closed time entries cannot be deleted'):
        task_entry.__class__.objects.filter(pk=task_entry.pk).delete()

    submission.closed = False
    submission.save()
    task_entry.delete()
    day_entry.delete()

    assert not task_entry.__class__.objects.filter(pk=task_entry.pk).exists()
    assert not day_entry.__class__.objects.filter(pk=day_entry.pk).exists()


def test_task_entry_cannot_be_created_in_closed_submission():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2024, 1, 1), date(2024, 2, 1)))
    task = TaskFactory(resource=resource, period=contract.period)
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-02-01'),
        closed=True,
    )

    with pytest.raises(ValidationError, match='Cannot modify time entries for submitted timesheets'):
        TaskEntryFactory(day_entry=day_entry, task=task)


def test_submission_report_uses_current_day_and_task_entry_format():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2025, 1, 1), date(2025, 2, 1)))
    special_leave_reason = SpecialLeaveReasonFactory()
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2025, 1, 1), date(2025, 2, 1)),
        timesheet={
            'days': ['2025-01-02'],
            'schedule': {'2025-01-02': 8},
            'day_entries': [
                {
                    'id': 10,
                    'day': '2025-01-02',
                    'contract': contract.pk,
                    'bank': '-2.00',
                    'due_hours': '8.00',
                    'special_leave_hours': '1.00',
                    'special_leave_reason': special_leave_reason.pk,
                    'protocol_number': 'PROTOCOL-1',
                    'is_sick': True,
                }
            ],
            'task_entries': [
                {
                    'id': 20,
                    'day_entry': 10,
                    'task': 100,
                    'day_shift_hours': '4.00',
                    'night_shift_hours': '1.00',
                    'on_call_hours': '0.00',
                    'travel_hours': '0.00',
                },
                {
                    'id': 21,
                    'day_entry': 10,
                    'task': 101,
                    'day_shift_hours': '2.00',
                    'night_shift_hours': '0.00',
                    'on_call_hours': '1.00',
                    'travel_hours': '3.00',
                },
            ],
        },
    )

    [report_day] = Krm3Day.from_submission(submission)

    assert report_day.submitted is True
    assert report_day.resource == resource
    assert report_day.contract == contract
    assert report_day.data_bank == Decimal('-2.00')
    assert report_day.data_bank_to is None
    assert report_day.data_bank_from == Decimal('2.00')
    assert report_day.data_day_shift == Decimal('6.00')
    assert report_day.data_night_shift == Decimal('1.00')
    assert report_day.data_on_call == Decimal('1.00')
    assert report_day.data_travel == Decimal('3.00')
    assert report_day.data_sick == Decimal('8.00')
    assert report_day.data_special_leave_hours == Decimal('1.00')
    assert report_day.data_special_leave_reason == special_leave_reason
    assert report_day.data_protocol_number == 'PROTOCOL-1'


def test_submission_report_reads_legacy_time_entry_format():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2025, 1, 1), date(2025, 2, 1)))
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2025, 1, 1), date(2025, 2, 1)),
        timesheet={
            'days': {'2025-01-02': {'hol': False, 'nwd': False, 'overtime': 1, 'meal_voucher': 1}},
            'schedule': {'2025-01-02': 8},
            'time_entries': [
                {
                    'id': 20,
                    'date': '2025-01-02',
                    'task': 100,
                    'bank_to': '2.00',
                    'bank_from': '0.00',
                    'day_shift_hours': '6.00',
                    'night_shift_hours': '1.00',
                    'on_call_hours': '2.00',
                    'travel_hours': '1.00',
                    'holiday_hours': '0.00',
                    'leave_hours': '0.00',
                    'special_leave_hours': '0.00',
                    'rest_hours': '0.00',
                    'sick_hours': '0.00',
                    'protocol_number': None,
                    'special_leave_reason': None,
                }
            ],
        },
    )

    [report_day] = Krm3Day.from_submission(submission)

    assert report_day.submitted is True
    assert report_day.resource == resource
    assert report_day.contract == contract
    assert report_day.data_bank == Decimal('2.00')
    assert report_day.data_bank_to == Decimal('2.00')
    assert report_day.data_bank_from is None
    assert report_day.data_day_shift == Decimal('6.00')
    assert report_day.data_night_shift == Decimal('1.00')
    assert report_day.data_on_call == Decimal('2.00')
    assert report_day.data_travel == Decimal('1.00')
    assert report_day.data_overtime == Decimal('1.00')
    assert report_day.data_meal_voucher == Decimal('1.00')
    assert report_day.data_regular_hours == Decimal('8.00')
