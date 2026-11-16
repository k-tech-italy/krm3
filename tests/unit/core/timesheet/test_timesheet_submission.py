import json
from datetime import date
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
    create_contract_without_scheduled_hours,
)

from krm3.core.models import TimesheetSubmission
from krm3.timesheet.rules import Krm3Day

def _day_entry(contract, day, hours='8.00'):
    return DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=day,
        day_hours=Decimal(hours),
        due_hours=Decimal('8.00'),
    )


def test_completeness_validation_rejects_an_incomplete_day_entry():
    contract = ContractFactory(
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    _day_entry(contract, date(2026, 9, 7), hours='6.00')
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission._verify_scheduled_hours_completed()


def test_completeness_validation_rejects_a_missing_day_entry_without_tasks():
    contract = ContractFactory(
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission._verify_scheduled_hours_completed()


def test_completeness_validation_accepts_complete_submission_without_tasks():
    contract = ContractFactory(
        period=(date(2026, 9, 7), date(2026, 9, 9)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    _day_entry(contract, date(2026, 9, 7))
    _day_entry(contract, date(2026, 9, 8))
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 7), date(2026, 9, 9)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    submission._verify_scheduled_hours_completed()

    assert not TaskFactory._meta.model.objects.filter(resource=contract.resource).exists()


def test_completeness_validation_ignores_days_outside_the_active_contract():
    contract = ContractFactory(
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    _day_entry(contract, date(2026, 9, 7))
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 7), date(2026, 9, 9)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    submission._verify_scheduled_hours_completed()


def test_completeness_validation_ignores_days_with_zero_required_hours():
    contract = ContractFactory(
        period=(date(2026, 9, 12), date(2026, 9, 14)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 12), date(2026, 9, 14)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    submission._verify_scheduled_hours_completed()


def test_completeness_validation_ignores_public_holidays():
    christmas = date(2026, 12, 25)
    contract = ContractFactory(
        period=(christmas, date(2026, 12, 26)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(christmas, date(2026, 12, 26)),
        status=TimesheetSubmission.Status.CLOSED,
    )

    assert contract.get_due_hours(christmas) == 0

    submission._verify_scheduled_hours_completed()


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps(
        {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}
    )
)
def test_completeness_validation_uses_default_schedule_when_contract_schedule_is_missing():
    contract = ContractFactory(
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        working_schedule={},
    )
    submission = TimesheetSubmissionFactory.build(
        resource=contract.resource,
        period=(date(2026, 9, 7), date(2026, 9, 8)),
        status=TimesheetSubmission.Status.CLOSED,
    )
    assert contract.get_due_hours(date(2026, 9, 7)) == 8

    with pytest.raises(ValidationError, match='The timesheet has incomplete scheduled days'):
        submission._verify_scheduled_hours_completed()


@pytest.mark.parametrize('reload_before_closing', (False, True))
def test_submission_snapshot_excludes_the_day_after_its_period(reload_before_closing):
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(
        resource,
        (date(2027, 4, 1), date(2027, 6, 1)),
    )
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
    submission = TimesheetSubmissionFactory.build(
        resource=resource,
        period=DateRange(date(2027, 4, 1), date(2027, 4, 30), '[]'),
        status=TimesheetSubmission.Status.DRAFT if reload_before_closing else TimesheetSubmission.Status.CLOSED,
    )
    submission.save()
    if reload_before_closing:
        submission.refresh_from_db()
        submission.status = TimesheetSubmission.Status.CLOSED
        submission.save()

    assert submission.timesheet['days'][-1] == '2027-04-30'
    assert {entry['id'] for entry in submission.timesheet['day_entries']} == {april_entry.pk}
    assert submission.timesheet['bank_hours'] == '0.00'
    assert 'status' not in submission.timesheet

    april_entry.refresh_from_db()
    may_entry.refresh_from_db()
    assert april_entry.closed is True
    assert may_entry.closed is False


def test_first_closed_submission_establishes_the_starting_point_despite_older_contracts():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), date(2026, 11, 1)))

    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-10-01', '2026-11-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    assert submission.is_closed is True


def test_cannot_close_a_timesheet_after_an_unsubmitted_contracted_month():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), date(2026, 4, 1)))
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-01-01', '2026-02-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    march = TimesheetSubmissionFactory.build(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    with pytest.raises(ValidationError, match='The timesheet for 2026-02 must be submitted first'):
        march.save()


def test_closing_skips_months_without_an_active_contract():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), date(2026, 2, 1)))
    create_contract_without_scheduled_hours(resource, (date(2026, 3, 1), date(2026, 4, 1)))
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-01-01', '2026-02-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    march = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    assert march.is_closed is True


def test_historical_gaps_before_the_latest_closed_submission_are_ignored():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), date(2026, 6, 1)))
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-04-01', '2026-05-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    may = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-05-01', '2026-06-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    assert may.is_closed is True


def test_closing_an_open_submission_checks_the_previous_contracted_month():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), date(2026, 4, 1)))
    TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-01-01', '2026-02-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )
    march = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        status=TimesheetSubmission.Status.DRAFT,
    )

    march.status = TimesheetSubmission.Status.CLOSED

    with pytest.raises(ValidationError, match='The timesheet for 2026-02 must be submitted first'):
        march.save()


def test_existing_closed_submission_is_not_revalidated_against_historical_gaps():
    resource = ResourceFactory()
    create_contract_without_scheduled_hours(resource, (date(2026, 3, 1), date(2026, 4, 1)))
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-03-01', '2026-04-01'),
        status=TimesheetSubmission.Status.CLOSED,
    )
    ContractFactory(resource=resource, period=(date(2026, 1, 1), date(2026, 3, 1)))

    submission.save()


def test_submission_state_is_synchronized_with_day_entries():
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2024, 1, 1), date(2024, 2, 1)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-01-08'),
        status=TimesheetSubmission.Status.CLOSED,
    )

    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is True

    submission.status = TimesheetSubmission.Status.DRAFT
    submission.save()
    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is False

    submission.status = TimesheetSubmission.Status.CLOSED
    submission.save()
    submission.delete()
    day_entry.refresh_from_db()
    assert day_entry.timesheet is None
    assert day_entry.closed is False


def test_closed_entries_cannot_be_deleted_until_submission_is_reopened():
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2024, 1, 1), date(2024, 2, 1)))
    task = TaskFactory(resource=resource, period=contract.period)
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    task_entry = TaskEntryFactory(day_entry=day_entry, task=task)
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-02-01'),
        status=TimesheetSubmission.Status.CLOSED,
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

    submission.status = TimesheetSubmission.Status.DRAFT
    submission.save()
    task_entry.delete()
    day_entry.delete()

    assert not task_entry.__class__.objects.filter(pk=task_entry.pk).exists()
    assert not day_entry.__class__.objects.filter(pk=day_entry.pk).exists()


def test_entries_cannot_be_changed_until_the_later_submission_is_reopened():
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2026, 9, 1), date(2026, 11, 1)))
    task = TaskFactory(resource=resource, period=contract.period)
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2026, 9, 15))
    task_entry = TaskEntryFactory(day_entry=day_entry, task=task)
    october = TimesheetSubmissionFactory(
        resource=resource,
        period=('2026-10-01', '2026-11-01'),
        status=TimesheetSubmission.Status.CLOSED,
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

    october.status = TimesheetSubmission.Status.DRAFT
    october.save()
    day_entry.full_clean()
    task_entry.save()


def test_submission_cannot_be_deleted_while_a_later_submission_is_closed():
    resource = ResourceFactory()
    september_period = ('2026-09-01', '2026-10-01')
    october_period = ('2026-10-01', '2026-11-01')
    september = TimesheetSubmissionFactory(
        resource=resource,
        period=september_period,
        status=TimesheetSubmission.Status.CLOSED,
    )
    TimesheetSubmissionFactory(
        resource=resource,
        period=october_period,
        status=TimesheetSubmission.Status.CLOSED,
    )

    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        september.delete()
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        september.__class__.objects.filter(pk=september.pk).delete()


def test_task_entry_cannot_be_created_in_closed_submission():
    resource = ResourceFactory()
    period = (date(2024, 1, 1), date(2024, 2, 1))
    contract = create_contract_without_scheduled_hours(resource, period)
    task = TaskFactory(resource=resource, period=contract.period)
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2024, 1, 3))
    TimesheetSubmissionFactory(
        resource=resource,
        period=period,
        status=TimesheetSubmission.Status.CLOSED,
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


def test_new_submission_defaults_to_draft():
    resource = ResourceFactory()

    submission = TimesheetSubmission.objects.create(
        resource=resource,
        period=DateRange(date(2026, 1, 1), date(2026, 2, 1), '[)'),
    )

    assert submission.status == TimesheetSubmission.Status.DRAFT
    assert submission.is_closed is False
    assert submission.is_submitted is False


def test_submission_status_properties_and_querysets():
    submissions = {
        status: TimesheetSubmissionFactory(
            resource=ResourceFactory(),
            period=(date(2026, 1, 1), date(2026, 2, 1)),
            status=status,
        )
        for status in TimesheetSubmission.Status
    }

    assert submissions[TimesheetSubmission.Status.DRAFT].is_closed is False
    assert submissions[TimesheetSubmission.Status.DRAFT].is_submitted is False
    assert submissions[TimesheetSubmission.Status.PENDING].is_closed is False
    assert submissions[TimesheetSubmission.Status.PENDING].is_submitted is True
    assert submissions[TimesheetSubmission.Status.REJECTED].is_closed is False
    assert submissions[TimesheetSubmission.Status.REJECTED].is_submitted is False
    assert submissions[TimesheetSubmission.Status.CLOSED].is_closed is True
    assert submissions[TimesheetSubmission.Status.CLOSED].is_submitted is True

    assert set(TimesheetSubmission.objects.all().submitted()) == {
        submissions[TimesheetSubmission.Status.PENDING],
        submissions[TimesheetSubmission.Status.CLOSED],
    }
    assert set(TimesheetSubmission.objects.all().closed()) == {submissions[TimesheetSubmission.Status.CLOSED]}


@pytest.mark.parametrize(
    ('submission_status', 'expected_closed'),
    [
        pytest.param(TimesheetSubmission.Status.DRAFT, False, id='draft'),
        pytest.param(TimesheetSubmission.Status.PENDING, True, id='pending'),
        pytest.param(TimesheetSubmission.Status.REJECTED, False, id='rejected'),
        pytest.param(TimesheetSubmission.Status.CLOSED, True, id='closed'),
    ],
)
def test_day_entry_closed_projection_tracks_submission_status(submission_status, expected_closed):
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2026, 9, 1), date(2026, 10, 1)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2026, 9, 2))

    TimesheetSubmissionFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 10, 1)),
        status=submission_status,
    )

    day_entry.refresh_from_db()
    assert day_entry.closed is expected_closed


def test_pending_submission_locks_day_entries():
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2026, 9, 1), date(2026, 10, 1)))
    day_entry = DayEntryFactory(resource=resource, contract=contract, day=date(2026, 9, 2))
    TimesheetSubmissionFactory(
        resource=resource,
        period=(date(2026, 9, 1), date(2026, 10, 1)),
        status=TimesheetSubmission.Status.PENDING,
    )

    with pytest.raises(ValidationError, match='Closed time entries cannot be deleted'):
        day_entry.delete()
