import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from constance.test import override_config
from django.core.exceptions import ValidationError
from psycopg.types.range import DateRange
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


def _complete_scheduled_day(resource, contract, day, *, entry=None):
    TaskFactory(resource=resource, period=(day, day + timedelta(days=1)))
    due_hours = contract.get_due_hours(day)
    if entry is None:
        return DayEntryFactory(
            resource=resource,
            contract=contract,
            day=day,
            day_hours=due_hours,
            due_hours=due_hours,
        )
    entry.day_hours = due_hours
    entry.due_hours = due_hours
    entry.save()
    return entry


def test_cannot_submit_without_assigned_tasks():
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=(date(2026, 9, 1), date(2026, 9, 2)))
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


def test_cannot_submit_with_incomplete_task_covered_day():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('7.00'),
        due_hours=Decimal('8.00'),
    )
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


def test_cannot_submit_with_missing_task_covered_day_entry():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=contract.period,
        closed=True,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


def test_can_submit_with_complete_day_covered_by_open_ended_task():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), None),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=(date(2026, 9, 1), None))
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )

    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )

    assert submission.closed is True


def test_overlapping_tasks_do_not_require_scheduled_hours_twice():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )

    submission = TimesheetSubmissionFactory(resource=resource, period=contract.period, closed=True)

    assert submission.closed is True


@pytest.mark.parametrize('absence_field', ('is_sick', 'asked_holiday'))
def test_full_day_absence_covers_scheduled_hours(absence_field):
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        due_hours=Decimal('8.00'),
        **{absence_field: True},
    )

    submission = TimesheetSubmissionFactory(resource=resource, period=contract.period, closed=True)

    assert submission.closed is True


def test_on_call_hours_do_not_cover_scheduled_hours():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        on_call_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )
    submission = TimesheetSubmissionFactory.build(resource=resource, period=contract.period, closed=True)

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


def test_submission_completeness_matches_frontend_hour_calculation():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('2.00'),
        night_hours=Decimal('1.00'),
        travel_hours=Decimal('1.00'),
        leave_hours=Decimal('1.00'),
        special_leave_hours=Decimal('1.00'),
        special_leave_reason=SpecialLeaveReasonFactory(),
        rest_hours=Decimal('1.00'),
        bank=Decimal('-1.00'),
        due_hours=Decimal('8.00'),
    )

    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )
    submission.save()

    assert submission.closed is True


def test_submission_skips_days_not_covered_by_assigned_task():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 3)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=(date(2026, 9, 1), date(2026, 9, 2)))
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )

    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 3)),
        closed=True,
    )
    submission.save()

    assert submission.closed is True


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 0, 'wed': 0, 'thu': 0, 'fri': 0, 'sat': 0, 'sun': 0})
)
def test_submission_uses_default_schedule_when_contract_schedule_is_empty():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        working_schedule={},
    )
    TaskFactory(resource=resource, period=contract.period)
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 7),
        day_hours=Decimal('7.00'),
        due_hours=Decimal('8.00'),
    )
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        closed=True,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


def test_submission_skips_public_holidays():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 1, 1), date(2026, 1, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8},
    )
    TaskFactory(resource=resource, period=contract.period)
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 1, 1), date(2026, 1, 2)),
        closed=True,
    )

    submission.save()

    assert submission.closed is True


def test_submission_skips_task_covered_days_without_active_contract():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
    )
    TaskFactory(resource=resource, period=contract.period)
    contract.__class__.objects.filter(pk=contract.pk).update(period=DateRange(date(2026, 9, 2), date(2026, 9, 3), '[)'))
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )

    submission.save()

    assert submission.closed is True


def test_resubmitting_revalidates_completeness():
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=contract.period)
    entry = DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2026, 9, 1),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 9, 2)),
        closed=True,
    )
    submission.closed = False
    submission.save()
    entry.day_hours = Decimal('7.00')
    entry.save()

    submission.closed = True
    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission.save()


@pytest.mark.parametrize('reload_before_closing', (False, True))
def test_submission_snapshot_excludes_the_day_after_its_period(reload_before_closing):
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2027, 4, 1), date(2027, 6, 1)))
    april_entry = DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2027, 4, 30),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
    )
    may_entry = DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2027, 5, 1),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('8.00'),
    )
    _complete_scheduled_day(resource, contract, april_entry.day, entry=april_entry)
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=DateRange(date(2027, 4, 1), date(2027, 4, 30), '[]'),
        closed=not reload_before_closing,
    )
    submission.save()
    if reload_before_closing:
        submission.refresh_from_db()
        submission.closed = True
        submission.save()

    assert submission.timesheet['days'][-1] == '2027-04-30'
    assert {entry['id'] for entry in submission.timesheet['day_entries']} == {april_entry.pk}
    assert submission.timesheet['bank_hours'] == '0.00'

    april_entry.refresh_from_db()
    may_entry.refresh_from_db()
    assert april_entry.closed is True
    assert may_entry.closed is False


def test_first_closed_submission_establishes_the_starting_point_despite_older_contracts():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 11, 1)))
    _complete_scheduled_day(resource, contract, date(2026, 10, 1))

    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-10-01', '2026-11-01'),
        closed=True,
    )

    assert submission.closed is True


def test_cannot_close_a_timesheet_after_an_unsubmitted_contracted_month():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 4, 1)))
    _complete_scheduled_day(resource, contract, date(2026, 1, 2))
    TimesheetSubmissionFactory(resource=resource, period=('2026-01-01', '2026-02-01'), closed=True)

    march = TimesheetSubmissionFactory.build(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        closed=True,
    )

    with pytest.raises(ValidationError, match='The timesheet for 2026-02 must be submitted first'):
        march.save()


def test_closing_skips_months_without_an_active_contract():
    resource = ResourceFactory()
    january_contract = ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 2, 1)))
    march_contract = ContractFactory(resource=resource, period=(date(2026, 3, 1), date(2026, 4, 1)))
    _complete_scheduled_day(resource, january_contract, date(2026, 1, 2))
    _complete_scheduled_day(resource, march_contract, date(2026, 3, 2))
    TimesheetSubmissionFactory(resource=resource, period=('2026-01-01', '2026-02-01'), closed=True)

    march = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        closed=True,
    )

    assert march.closed is True


def test_historical_gaps_before_the_latest_closed_submission_are_ignored():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 6, 1)))
    _complete_scheduled_day(resource, contract, date(2026, 4, 1))
    _complete_scheduled_day(resource, contract, date(2026, 5, 1))
    TimesheetSubmissionFactory(resource=resource, period=('2026-04-01', '2026-05-01'), closed=True)

    may = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-05-01', '2026-06-01'),
        closed=True,
    )

    assert may.closed is True


def test_closing_an_open_submission_checks_the_previous_contracted_month():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 4, 1)))
    _complete_scheduled_day(resource, contract, date(2026, 1, 2))
    TimesheetSubmissionFactory(resource=resource, period=('2026-01-01', '2026-02-01'), closed=True)
    march = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        closed=False,
    )

    march.closed = True

    with pytest.raises(ValidationError, match='The timesheet for 2026-02 must be submitted first'):
        march.save()


def test_existing_closed_submission_is_not_revalidated_against_historical_gaps():
    resource = ResourceFactory()
    TaskFactory(resource=resource, period=(date(2026, 3, 1), date(2026, 3, 2)), contract=True)
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        closed=True,
    )
    ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 3, 1)))

    submission.save()


def test_submission_state_is_synchronized_with_day_entries():
    resource = ResourceFactory()
    day_entry = DayEntryFactory(resource=resource, day=date(2024, 1, 3))
    _complete_scheduled_day(resource, day_entry.contract, day_entry.day, entry=day_entry)
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
    task = TaskFactory(resource=resource, period=(date(2024, 1, 3), date(2024, 1, 4)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    task_entry = TaskEntryFactory(day_entry=day_entry, task=task)
    day_entry.day_hours = day_entry.due_hours = contract.get_due_hours(day_entry.day)
    day_entry.save()
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


def test_entries_cannot_be_changed_until_the_later_submission_is_reopened():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 9, 1), date(2026, 11, 1)))
    task = TaskFactory(resource=resource, period=(date(2026, 9, 15), date(2026, 9, 16)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2026, 9, 15))
    task_entry = TaskEntryFactory(day_entry=day_entry, task=task)
    _complete_scheduled_day(resource, contract, date(2026, 10, 5))
    october = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-10-01', '2026-11-01'),
        closed=True,
    )

    day_entry.comment = 'Changed'
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        day_entry.full_clean()

    task_entry.comment = 'Changed'
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        task_entry.save()

    new_day_entry = DayEntryFactory.build(resource=resource, contract=contract, day=date(2026, 9, 16))
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        new_day_entry.full_clean()

    new_task = TaskFactory(resource=resource, period=contract.period)
    new_task_entry = TaskEntryFactory.build(day_entry=day_entry, task=new_task)
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        new_task_entry.save()

    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        day_entry.delete()
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        task_entry.delete()

    october.closed = False
    october.save()
    day_entry.full_clean()
    task_entry.save()


def test_submission_cannot_be_deleted_while_a_later_submission_is_closed():
    resource = ResourceFactory()
    TaskFactory(resource=resource, period=(date(2026, 9, 6), date(2026, 9, 7)), contract=True)
    TaskFactory(resource=resource, period=(date(2026, 10, 4), date(2026, 10, 5)), contract=True)
    september = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-09-01', '2026-10-01'),
        closed=True,
    )
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-10-01', '2026-11-01'),
        closed=True,
    )

    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        september.delete()
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        september.__class__.objects.filter(pk=september.pk).delete()


def test_task_entry_cannot_be_created_in_closed_submission():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2024, 1, 1), date(2024, 2, 1)))
    task = TaskFactory(resource=resource, period=(date(2024, 1, 3), date(2024, 1, 4)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    day_entry.day_hours = day_entry.due_hours = contract.get_due_hours(day_entry.day)
    day_entry.save()
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
