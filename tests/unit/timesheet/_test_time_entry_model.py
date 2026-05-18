import datetime
import json
from contextlib import nullcontext as does_not_raise
from decimal import Decimal
from constance.test import override_config

import freezegun

from krm3.timesheet.rules import Krm3Day
import pytest
from django.core import exceptions

from krm3.utils.dates import KrmDay
from testutils.date_utils import _dt
from testutils.factories import (
    BasketFactory,
    ContactFactory,
    InvoiceEntryFactory,
    ProjectFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TaskEntryFactory,
    TimesheetSubmissionFactory, POFactory, DayEntryFactory,
)

from krm3.core.models.timesheets import TaskEntry


# @override_config(
#     DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
# )
# @pytest.mark.parametrize(
#     ('hour_field', 'expected_behavior'),
#     (
#         pytest.param('sick_hours', does_not_raise(), id='sick'),
#         pytest.param('holiday_hours', does_not_raise(), id='holiday'),
#         pytest.param('leave_hours', does_not_raise(), id='leave'),
#         pytest.param('special_leave_hours', does_not_raise(), id='special_leave'),
#         pytest.param('on_call_hours', pytest.raises(exceptions.ValidationError), id='on_call'),
#         pytest.param('night_shift_hours', pytest.raises(exceptions.ValidationError), id='night_shift'),
#         pytest.param('travel_hours', pytest.raises(exceptions.ValidationError), id='travel'),
#         pytest.param('rest_hours', does_not_raise(), id='rest'),
#     ),
# )
# def test_day_entry_is_saved_only_with_sick_holiday_rest_or_leave_hours(hour_field, expected_behavior):
#     with expected_behavior:
#         day_entry = DayEntryFactory(day=_dt('2025-07-14'))
#
#         entry = TaskEntryFactory(
#             day_entry=day_entry,
#             task=None,
#             day_shift_hours=0,
#             special_leave_reason=SpecialLeaveReasonFactory() if hour_field == 'special_leave_hours' else None,
#             **{hour_field: 8},
#         )
#         # NOTE: asserting the obvious to appease Ruff :^)
#         assert entry.task is None

@pytest.mark.parametrize(
    'hour_field',
    (
        pytest.param('day_shift_hours', id='day_shift'),
        # pytest.param('sick_hours', id='sick'),
        # pytest.param('holiday_hours', id='holiday'),
        # pytest.param('leave_hours', id='leave'),
        # pytest.param('special_leave_hours', id='special_leave'),
        pytest.param('on_call_hours', id='on_call'),
        pytest.param('night_shift_hours', id='night_shift'),
        pytest.param('travel_hours', id='travel'),
        # pytest.param('rest_hours', id='rest'),
    ),
)
def test_rejects_negative_hours(hour_field):
    resource = ResourceFactory()
    time_logged = {'day_shift_hours': 0} | {hour_field: -1}
    with pytest.raises(exceptions.ValidationError):
        TaskEntryFactory(
            task=(
                TaskFactory(
                    project=ProjectFactory(period=(_dt('2020-01-01'), None)),
                    resource=resource,
                    period=(_dt('2020-01-01'), None),
                    **{hour_field: }
                )
                if hour_field in ('day_shift_hours', 'night_shift_hours', 'travel_hours', 'on_call_hours')
                else None
            ),
            special_leave_reason=SpecialLeaveReasonFactory() if hour_field == 'special_leave_hours' else None,
            **time_logged,
        )

@pytest.mark.parametrize(
    'hour_field',
    (
        pytest.param('day_shift_hours', id='day_shift'),
        pytest.param('sick_hours', id='sick'),
        pytest.param('holiday_hours', id='holiday'),
        pytest.param('leave_hours', id='leave'),
        pytest.param('special_leave_hours', id='special_leave'),
        pytest.param('on_call_hours', id='on_call'),
        pytest.param('night_shift_hours', id='night_shift'),
        pytest.param('travel_hours', id='travel'),
        pytest.param('rest_hours', id='rest'),
        pytest.param('bank_from', id='bank_from'),
        pytest.param('bank_to', id='bank_to'),
    ),
)
def test_rejects_too_many_hours(hour_field):
    resource = ResourceFactory()
    time_logged = {'day_shift_hours': 0} | {hour_field: 25}
    with pytest.raises(exceptions.ValidationError):
        TaskEntryFactory(
            date=_dt('2024-01-01'),
            task=(
                TaskFactory(
                    project=ProjectFactory(period=(_dt('2020-01-01'), None)),
                    resource=resource,
                    period=(_dt('2020-01-01'), None),
                )
                if hour_field in ('day_shift_hours', 'night_shift_hours', 'travel_hours', 'on_call_hours')
                else None
            ),
            special_leave_reason=SpecialLeaveReasonFactory() if hour_field == 'special_leave_hours' else None,
            **time_logged,
        )

def test_rejects_too_many_day_shift_hours():
    project = ProjectFactory(period=(_dt('2020-01-01'), None))
    resource = ResourceFactory()
    with pytest.raises(exceptions.ValidationError):
        TaskEntryFactory(
            date=_dt('2024-01-01'),
            resource=resource,
            task=TaskFactory(project=project, resource=resource, period=(_dt('2020-01-01'), None)),
            day_shift_hours=Decimal(16.25),
        )

def test_rejects_too_many_night_shift_hours():
    project = ProjectFactory(period=(_dt('2020-01-01'), None))
    resource = ResourceFactory()
    with pytest.raises(exceptions.ValidationError):
        TaskEntryFactory(
            date=_dt('2024-01-01'),
            resource=resource,
            task=TaskFactory(project=project, resource=resource, period=(_dt('2020-01-01'), None)),
            day_shift_hours=0,
            night_shift_hours=Decimal(8.25),
        )

def test_rejects_both_bank_deposit_and_withdrawal_same_day():
    """Test that you cannot both deposit to and withdraw from bank on same day."""
    resource = ResourceFactory()
    with pytest.raises(
        exceptions.ValidationError, match='Cannot both withdraw from and deposit to bank hours on the same day'
    ):
        TaskEntryFactory(
            day_shift_hours=0,
            bank_from=2,
            bank_to=3,
            resource=resource,
        )

def test_bank_hours_included_in_total_hours_calculation():
    """Test that bank hours are properly included in total_hours calculation."""
    project = ProjectFactory(period=(_dt('2020-01-01'), None))
    resource = ResourceFactory()
    entry1 = TaskEntryFactory(
        day_shift_hours=10,
        task=TaskFactory(project=project, resource=resource, period=(_dt('2020-01-01'), None)),
        resource=resource,
    )
    TaskEntryFactory(
        day_shift_hours=0,
        bank_to=2,
        date=entry1.date,
        resource=resource,
    )

    daily_entries = TimeEntry.objects.filter(resource=resource, date=entry1.date)
    total_day_hours_with_deposit = sum(entry.total_hours for entry in daily_entries)
    assert total_day_hours_with_deposit == 8

    entry2 = TaskEntryFactory(
        day_shift_hours=6,
        task=TaskFactory(project=project, resource=resource),
        resource=resource,
        date=_dt('2020-03-04'),
    )
    TaskEntryFactory(
        day_shift_hours=0,
        bank_from=2,
        date=entry2.date,
        resource=resource,
    )
    daily_entries = TimeEntry.objects.filter(resource=resource, date=entry2.date)
    total_day_hours_with_withdrawal = sum(entry.total_hours for entry in daily_entries)
    assert total_day_hours_with_withdrawal == 8

def test_bank_hours_with_day_entry():
    """Test that bank hours can be used with day entries (non-task)."""
    resource = ResourceFactory()

    entry = TaskEntryFactory(
        task=None,
        resource=resource,
        date=_dt('2025-08-20'),
        day_shift_hours=0,
        leave_hours=3,
        bank_from=2,
        bank_to=0,
    )
    assert entry.total_hours == 5

def test_rejects_bank_deposit_exceeding_upper_limit():
    """Test that bank deposit is rejected if it would exceed upper balance limit."""
    project = ProjectFactory()
    resource = ResourceFactory()
    task = TaskFactory(project=project, resource=resource)
    TaskEntryFactory(
        date=_dt('2025-01-02'),
        resource=resource,
        task=task,
        day_shift_hours=16,
    )
    TaskEntryFactory(
        date=_dt('2025-01-03'),
        resource=resource,
        task=task,
        day_shift_hours=16,
    )
    TaskEntryFactory(
        date=_dt('2025-01-10'),
        resource=resource,
        task=task,
        day_shift_hours=10,
    )
    TaskEntryFactory(
        date=_dt('2025-01-02'),
        resource=resource,
        day_shift_hours=0,
        bank_to=8,
    )
    TaskEntryFactory(
        date=_dt('2025-01-03'),
        resource=resource,
        day_shift_hours=0,
        bank_to=8,
    )

    with pytest.raises(exceptions.ValidationError, match='This transaction would exceed the maximum bank balance'):
        TaskEntryFactory(
            date=_dt('2025-01-10'),
            resource=resource,
            day_shift_hours=0,
            bank_to=2,
        )

def test_rejects_bank_deposit_exceeding_lower_limit():
    """Test that bank deposit is rejected if it would exceed upper balance limit."""
    project = ProjectFactory()
    resource = ResourceFactory()
    task = TaskFactory(project=project, resource=resource)
    TaskEntryFactory(
        date=_dt('2024-01-02'),
        resource=resource,
        task=task,
        day_shift_hours=2,
        bank_from=8,
    )
    TaskEntryFactory(
        date=_dt('2024-01-03'),
        resource=resource,
        task=task,
        day_shift_hours=4,
        bank_from=4,
    )

    with pytest.raises(exceptions.ValidationError, match='This transaction would exceed the minimum bank balance'):
        TaskEntryFactory(
            resource=resource,
            task=task,
            day_shift_hours=2,
            bank_from=6,
        )

def test_holiday_rejects_any_bank_transactions():
    """Test that holiday entries cannot have any bank transactions."""
    resource = ResourceFactory()

    with pytest.raises(exceptions.ValidationError, match='Cannot use bank hours during holidays'):
        TaskEntryFactory(
            task=None,
            resource=resource,
            day_shift_hours=0,
            holiday_hours=8,
            bank_to=2,
            bank_from=0,
        )

    with pytest.raises(exceptions.ValidationError, match='Cannot use bank hours during holidays'):
        TaskEntryFactory(
            task=None,
            resource=resource,
            day_shift_hours=0,
            holiday_hours=8,
            bank_to=0,
            bank_from=2,
        )

@pytest.mark.parametrize(
    'day_entry_field',
    (
        pytest.param('leave_hours', id='leave'),
        pytest.param('rest_hours', id='rest'),
        pytest.param('special_leave_hours', id='special_leave'),
    ),
)
def test_day_entries_reject_bank_deposits(day_entry_field):
    """Test that all day entries reject bank deposits."""
    resource = ResourceFactory()
    kwargs = {
        'task': None,
        'resource': resource,
        'day_shift_hours': 0,
        'bank_to': 2,
        'bank_from': 0,
        day_entry_field: 10,
    }

    if day_entry_field == 'special_leave_hours':
        kwargs['special_leave_reason'] = SpecialLeaveReasonFactory()

    with pytest.raises(exceptions.ValidationError, match='Cannot deposit bank hours during'):
        TaskEntryFactory(**kwargs)

def test_bank_hours_with_scheduled_hours():
    resource = ResourceFactory()
    project = ProjectFactory()
    task = TaskFactory(project=project, resource=resource)
    date = _dt('2025-01-14')
    TaskEntryFactory(
        date=date,
        resource=resource,
        task=task,
        day_shift_hours=6,
    )
    time_deposit = TaskEntryFactory.build(task=None, resource=resource, date=date, day_shift_hours=0, bank_to=2)

    with pytest.raises(exceptions.ValidationError, match='Cannot deposit 2 bank hours'):
        time_deposit.save()

    time_withdraw = TaskEntryFactory.build(task=None, resource=resource, date=date, day_shift_hours=0, bank_from=5)
    with pytest.raises(exceptions.ValidationError, match='Cannot withdraw bank hours when task hours'):
        time_withdraw.save()

def test_bank_deposit_success_with_correct_custom_schedule():
    start_dt = _dt('2020-01-01')
    end_dt = _dt('2026-01-01')
    contract = ContractFactory(
        period=(start_dt, end_dt),
        working_schedule={'fri': 3, 'mon': 3, 'sat': 0, 'sun': 0, 'thu': 3, 'tue': 3, 'wed': 3},
    )
    project = ProjectFactory()
    resource = contract.resource
    task = TaskFactory(project=project, resource=resource)
    date = _dt('2025-01-14')
    TaskEntryFactory(
        date=date,
        resource=resource,
        task=task,
        day_shift_hours=4,
    )
    time_deposit = TaskEntryFactory(task=None, resource=resource, date=date, day_shift_hours=0, bank_to=1)

    assert time_deposit.bank_to == 1

def test_bank_deposit_with_0_scheduled_hours():
    date = _dt('2025-09-21')  # Sunday
    resource = ResourceFactory()
    with pytest.raises(exceptions.ValidationError, match='Cannot deposit 1 bank hours.'):
        TaskEntryFactory(task=None, resource=resource, date=date, day_shift_hours=0, bank_to=1)

    TaskEntryFactory(date=date, resource=resource, task=TaskFactory(resource=resource), day_shift_hours=1)
    time_deposit_at_weekend = TaskEntryFactory(
        task=None, resource=resource, date=date, day_shift_hours=0, bank_to=1
    )
    assert time_deposit_at_weekend.bank_to == 1

_day_entry_fields = ('sick_hours', 'holiday_hours', 'leave_hours', 'rest_hours', 'special_leave_hours')
_task_entry_fields = ('day_shift_hours', 'night_shift_hours', 'travel_hours', 'on_call_hours')
_bank_fields = ('bank_from', 'bank_to')
_all_hours_and_bank_fields = (*_day_entry_fields, *_task_entry_fields, *_bank_fields)

@pytest.mark.parametrize('field', _all_hours_and_bank_fields)
def test_rejects_time_entries_with_negative_hours(field):
    task = TaskFactory()
    task_entry_kwargs = {'task': task, 'resource': task.resource} if field in _task_entry_fields else {}
    entry_kwargs = {'day_shift_hours': 8} | task_entry_kwargs | {field: -1}
    with pytest.raises(exceptions.ValidationError, match='must be 0 or greater'):
        TaskEntryFactory(**entry_kwargs)

def test_rejects_time_entries_with_all_hours_and_bank_fields_set_to_zero():
    with pytest.raises(exceptions.ValidationError, match='must be greater than 0'):
        TaskEntryFactory(day_shift_hours=0)

def test_is_saved_with_all_task_entry_hours_filled():
    """Non-zero total hours on a task, all non-full-day non-task hours fields filled"""
    task = TaskFactory()
    entry = TaskEntryFactory(day_shift_hours=8, task=task, resource=task.resource)
    entry.night_shift_hours = 2.5
    entry.travel_hours = 1
    entry.day_shift_hours = 4.5
    entry.on_call_hours = 2
    with does_not_raise():
        entry.save()

    # NOTE: asserting the obvious to appease Ruff :^)
    entry.refresh_from_db()
    assert entry.travel_hours + entry.day_shift_hours + entry.night_shift_hours == 8
    assert entry.on_call_hours == 2

def test_is_deposit_deleted_after_task_entry_hours_deleted():
    """No negative hours when clearing working hours"""
    date = _dt('2025-01-14')
    task = TaskFactory()
    entry = TaskEntryFactory(date=date, day_shift_hours=10, task=task, resource=task.resource)
    deposit = TaskEntryFactory(date=date, day_shift_hours=0, bank_to=2, task=None, resource=task.resource)
    entry.delete()
    with pytest.raises(TimeEntry.DoesNotExist):
        deposit.refresh_from_db()

@pytest.mark.parametrize('existing_hours_field', _day_entry_fields)
@pytest.mark.parametrize('new_hours_field', _day_entry_fields)
def test_day_entry_overwrites_other_existing_day_entry_on_the_same_day(existing_hours_field, new_hours_field):
    resource = ResourceFactory()
    absence_day = _dt('2024-01-03')
    _absence_entry = TaskEntryFactory(
        date=absence_day,
        day_shift_hours=0,
        resource=resource,
        special_leave_reason=SpecialLeaveReasonFactory() if existing_hours_field == 'special_leave_hours' else None,
        **{existing_hours_field: 8},
    )
    assert TimeEntry.objects.day_entries().filter(date=absence_day, resource=resource).count() == 1  # pyright: ignore

    with does_not_raise():
        # the same resource should be able to log their absence on
        # a different available day
        _absence_entry_on_other_day = TaskEntryFactory(
            date=_dt('2024-01-02'),
            day_shift_hours=0,
            resource=resource,
            special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
            **{new_hours_field: 8},
        )

        # another resource should be able to log their own absence
        # entry on the same day...
        other_resource = ResourceFactory()
        _absence_entry_for_other_resource = TaskEntryFactory(
            date=absence_day,
            day_shift_hours=0,
            resource=other_resource,
            special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
            **{new_hours_field: 8},
        )

    _new_entry = TaskEntryFactory(
        date=absence_day,
        day_shift_hours=0,
        resource=resource,
        special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
        **{new_hours_field: 8},
    )
    day_entries = TimeEntry.objects.day_entries().filter(date=absence_day, resource=resource)  # pyright: ignore
    assert day_entries.count() == 1
    assert getattr(day_entries.get(), new_hours_field) == 8

@pytest.mark.parametrize('field', _task_entry_fields)
def test_task_entry_is_saved_only_when_no_other_task_entry_exists_on_the_same_day_for_the_same_task(field):
    resource = ResourceFactory()
    project = ProjectFactory()
    task = TaskFactory(title='whoops', project=project, start_date=project.start_date, resource=resource)
    other_task = TaskFactory(title='good', project=project, start_date=project.start_date, resource=resource)
    work_day = _dt('2024-01-01')

    def _make_time_entry(**kwargs):
        factory_kwargs = {'date': work_day, 'task': task, 'resource': resource, 'day_shift_hours': 0} | kwargs
        return TaskEntryFactory(**factory_kwargs)

    _existing_time_entry = _make_time_entry(day_shift_hours=2)

    # the resource should be able to log their time for another
    # available day on the same task
    _new_time_entry_on_other_day = _make_time_entry(date=_dt('2024-01-02'), task=other_task, **{field: 2})
    assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 1  # pyright: ignore

    # the resource should be able to log their time for the same
    # day on another available task
    _new_time_entry_on_other_task = _make_time_entry(task=other_task, **{field: 6})
    assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 2  # pyright: ignore

    _overwriting_entry = _make_time_entry(**{field: 2})
    assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 2  # pyright: ignore

def test_is_saved_as_sick_day():
    """Sick day with no work or task-related hours logged"""
    entry = TaskEntryFactory(day_shift_hours=8, task=TaskFactory())
    entry.day_shift_hours = 0
    entry.sick_hours = 8

    with pytest.raises(exceptions.ValidationError, match='non-task hours in a task entry'):
        entry.save()

    entry.task = None
    entry.save()
    # NOTE: asserting the obvious to appease Ruff :^)
    entry.refresh_from_db()
    assert entry.day_shift_hours == 0
    assert entry.sick_hours == 8

def test_protocol_number_without_sick_hours():
    """Protocol number field cannot be set without sick hours logged."""
    with pytest.raises(exceptions.ValidationError, match='Protocol number can be used only for sick days'):
        TaskEntryFactory(task=None, protocol_number='123', sick_hours=0, resource=ResourceFactory())

def test_protocol_number_with_wrong_format():
    """Protocol number field values must be all digits."""
    with pytest.raises(exceptions.ValidationError, match='Protocol number digits must be numeric'):
        TaskEntryFactory(task=None, protocol_number='3.1415', sick_hours=8, resource=ResourceFactory())

def test_sick_hours_protocol_number_success():
    """Test Protocol number with correct format with sick hours."""
    with does_not_raise():
        TaskEntryFactory(
            task=None, protocol_number='00032100', sick_hours=8, day_shift_hours=0, resource=ResourceFactory()
        )

def test_is_saved_as_holiday():
    """Sick day with no work or task-related hours logged"""
    entry = TaskEntryFactory(day_shift_hours=8, task=TaskFactory())
    entry.day_shift_hours = 0
    entry.holiday_hours = 8

    with pytest.raises(exceptions.ValidationError, match='non-task hours in a task entry'):
        entry.save()

    entry.task = None
    entry.save()
    # NOTE: asserting the obvious to appease Ruff :^)
    entry.refresh_from_db()
    assert entry.day_shift_hours == 0
    assert entry.holiday_hours == 8

def test_is_saved_as_leave():
    """Leave hours with no work or task-related hours logged"""
    entry = TaskEntryFactory(date=_dt('2025-09-09'), day_shift_hours=8, task=TaskFactory())
    entry.day_shift_hours = 0
    entry.leave_hours = 8

    with pytest.raises(exceptions.ValidationError, match='non-task hours in a task entry'):
        entry.save()

    entry.task = None
    entry.save()
    # NOTE: asserting the obvious to appease Ruff :^)
    entry.refresh_from_db()
    assert entry.day_shift_hours == 0
    assert entry.leave_hours == 8

@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
)
def test_is_saved_as_special_leave():
    """Special leave hours with no work or task-related hours logged"""
    entry = TaskEntryFactory(day_shift_hours=8, task=TaskFactory(), date=_dt('20250102'))
    entry.day_shift_hours = 0
    entry.special_leave_hours = 8
    entry.task = None
    with pytest.raises(exceptions.ValidationError, match='Reason is required'):
        entry.save()

    entry.special_leave_reason = SpecialLeaveReasonFactory()
    entry.save()
    # NOTE: asserting the obvious to appease Ruff :^)
    entry.refresh_from_db()
    assert entry.day_shift_hours == 0
    assert entry.special_leave_hours == 8
    assert entry.special_leave_reason

def test_raises_if_more_than_one_absence_fields_is_filled():
    # NOTE: we are specifying a date to guarantee that we can
    #       actually log a leave. If we can't guarantee it, then
    #       this test has the chance of failing because the factory
    #       might pick (pseudo-randomly) a non-working day, and you
    #       can't log a leave on a non-working day.
    #       2026-01-02 is a Friday.
    entry = TaskEntryFactory(date=_dt('2026-01-02'), day_shift_hours=0, leave_hours=1)
    entry.sick_hours = 4
    entry.holiday_hours = 4
    with pytest.raises(exceptions.ValidationError, match='more than one kind of non-task hours in a day'):
        entry.save()

def test_raises_if_logging_work_during_sick_days():
    entry = TaskEntryFactory(day_shift_hours=4, task=TaskFactory())
    entry.sick_hours = 4
    with pytest.raises(exceptions.ValidationError, match='task hours and non-task hours together'):
        entry.save()

def test_raises_if_logging_work_during_holidays():
    entry = TaskEntryFactory(day_shift_hours=4, task=TaskFactory())
    entry.holiday_hours = 4
    with pytest.raises(exceptions.ValidationError, match='task hours and non-task hours together'):
        entry.save()

@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
)
@pytest.mark.parametrize(
    ('hours_key', 'expected_to_raise'),
    (
        pytest.param(
            'day_shift_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='day'
        ),
        pytest.param(
            'night_shift_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='night'
        ),
        pytest.param(
            'rest_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='rest'
        ),
        pytest.param(
            'travel_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='travel'
        ),
        pytest.param(
            'on_call_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='on_call'
        ),
        pytest.param(
            'sick_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='sick'
        ),
        pytest.param(
            'holiday_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='holiday'
        ),
        pytest.param(
            'leave_hours', pytest.raises(exceptions.ValidationError, match='Only a special leave'), id='leave'
        ),
        pytest.param('special_leave_hours', does_not_raise(), id='special_leave'),
    ),
)
def test_raises_if_special_leave_reason_not_on_special_leave_entry(hours_key, expected_to_raise):
    hours = {'day_shift_hours': 0} | {hours_key: 8}
    reason = SpecialLeaveReasonFactory()
    with expected_to_raise:
        TaskEntryFactory(
            date=_dt('2025-10-21'),
            task=(
                None
                if str(hours_key).removesuffix('_hours') in ('sick', 'holiday', 'leave', 'special_leave')
                else TaskFactory()
            ),
            special_leave_reason=reason,
            **hours,
        )

def test_raises_if_special_leave_has_invalid_reason():
    valid_reason = SpecialLeaveReasonFactory(title='valid')

    with does_not_raise():
        entry = TaskEntryFactory(
            date=_dt('2024-01-02'),
            day_shift_hours=0,
            special_leave_hours=2,
            special_leave_reason=valid_reason,
        )

    expired_reason = SpecialLeaveReasonFactory(title='expired', to_date=_dt('2020-01-02'))
    entry.special_leave_reason = expired_reason
    with pytest.raises(exceptions.ValidationError, match='Reason "expired" is not valid'):
        entry.save()

    upcoming_reason = SpecialLeaveReasonFactory(title='upcoming', from_date=_dt('2025-01-02'))
    entry.special_leave_reason = upcoming_reason
    with pytest.raises(exceptions.ValidationError, match='Reason "upcoming" is not valid'):
        entry.save()

def test_raises_if_ends_before_starting():
    with does_not_raise():
        # edge case: one day long special leave reason
        _valid = SpecialLeaveReasonFactory(from_date=_dt('2024-01-01'), to_date=_dt('2024-01-01'))

    with pytest.raises(exceptions.ValidationError, match='must not be later'):
        _should_fail = SpecialLeaveReasonFactory(
            from_date=_dt('2024-01-01'), to_date=_dt('2020-01-01')
        )

@pytest.mark.parametrize(
    'time_entry_date, expected_assigned_timesheet_index',
    [
        (_dt('2020-05-15'), 0),
        (_dt('2020-06-15'), 1),
        (_dt('2020-07-15'), 2),
        (_dt('2020-05-31'), 0),
        (_dt('2020-06-01'), 1),
        (_dt('2020-08-15'), None),
        (_dt('2020-04-15'), None),
    ],
)
def test_time_entry_should_be_assigned_to_appropriate_timesheet(
    time_entry_date, expected_assigned_timesheet_index
):
    resource = ResourceFactory()
    task = TaskFactory()
    TaskEntryFactory(date=time_entry_date, resource=resource, task=task)

    timesheets = []

    timesheets.append(
        TimesheetSubmissionFactory(resource=resource, closed=True, period=(_dt('2020-05-01'), _dt('2020-06-01')))
    )
    timesheets.append(
        TimesheetSubmissionFactory(resource=resource, closed=True, period=(_dt('2020-06-01'), _dt('2020-07-01')))
    )
    timesheets.append(
        TimesheetSubmissionFactory(resource=resource, closed=True, period=(_dt('2020-07-01'), _dt('2020-08-01')))
    )

    for i, timesheet in enumerate(timesheets):
        expected_count = 1 if i == expected_assigned_timesheet_index else 0
        assert timesheet.timeentry_set.count() == expected_count

def test_deleting_timesheet_should_set_key_to_none():
    resource = ResourceFactory()
    task = TaskFactory()
    time_entry = TaskEntryFactory(date=_dt('2020-05-15'), resource=resource, task=task)

    timesheet = TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2020-05-01'), _dt('2020-06-01'))
    )

    time_entry.refresh_from_db()
    assert timesheet.timeentry_set.count() == 1
    assert time_entry.timesheet == timesheet
    timesheet.delete()
    time_entry.refresh_from_db()
    assert time_entry.timesheet is None

def updating_timeentry_date_should_update_assigned_timesheet():
    resource = ResourceFactory()
    task = TaskFactory()
    time_entry = TaskEntryFactory(date=_dt('2020-05-15'), resource=resource, task=task)
    timesheet_1 = TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2020-05-01'), _dt('2020-06-01'))
    )
    timesheet_2 = TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2020-06-01'), _dt('2020-06-01'))
    )
    assert time_entry.timesheet == timesheet_1
    time_entry.date = _dt('2020-06-15')
    time_entry.save()
    assert time_entry.timesheet == timesheet_2

def test_timesheet_submission_str():
    from psycopg.types.range import DateRange

    timesheet = TimesheetSubmissionFactory(
        period=DateRange(_dt('2020-05-01'), _dt('2020-05-31'), '[]')
    )
    assert str(timesheet) == '2020-05-01 - 2020-05-30'

def test_rejects_time_entry_on_submitted_timesheet():
    """Test that time entries cannot be created or modified on submitted timesheets."""
    resource = ResourceFactory()
    task = TaskFactory(resource=resource)
    date = _dt('2020-05-15')

    # Should be able to create time entries when timesheet is not submitted
    with does_not_raise():
        TaskEntryFactory(date=date, resource=resource, task=task, day_shift_hours=8)

    # Create a submitted timesheet for this period
    TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2020-05-01'), _dt('2020-06-01'))
    )

    # Should not be able to create a new time entry in the submitted period
    with pytest.raises(exceptions.ValidationError, match='Cannot modify time entries for submitted timesheets'):
        TaskEntryFactory(date=date, resource=resource, task=task, day_shift_hours=8)

    # Should be able to create time entries outside the submitted period
    with does_not_raise():
        TaskEntryFactory(date=_dt('2020-06-15'), resource=resource, task=task, day_shift_hours=8)


@freezegun.freeze_time(_dt('2025-12-10'))
def test_empty_special_leave_reason_regression():
        timesheet_data = """{
  "days": {
    "2025-12-01": {
      "hol": false,
      "nwd": false,
      "closed": false,
      "bank_to": 0,
      "overtime": 0,
      "bank_from": 0,
      "rest_hours": 0,
      "sick_hours": 0,
      "leave_hours": 0,
      "meal_voucher": null,
      "travel_hours": 0,
      "holiday_hours": 0,
      "on_call_hours": 0,
      "day_shift_hours": 8,
      "night_shift_hours": 0,
      "special_leave_hours": 0,
      "special_leave_reason": null
    },
    "2025-12-02": {
      "hol": false,
      "nwd": false,
      "closed": false,
      "bank_to": 0,
      "overtime": 0,
      "bank_from": 0,
      "rest_hours": 0,
      "sick_hours": 0,
      "leave_hours": 0,
      "meal_voucher": null,
      "travel_hours": 0,
      "holiday_hours": 0,
      "on_call_hours": 0,
      "day_shift_hours": 8,
      "night_shift_hours": 0,
      "special_leave_hours": 0,
      "special_leave_reason": null
    }
  },
  "tasks": [
    {
      "id": 16,
      "color": null,
      "title": "Some task",
      "end_date": null,
      "admin_url": "",
      "start_date": "2025-12-01",
      "client_name": "Some client",
      "basket_title": null,
      "project_name": "Some project"
    }
  ],
  "schedule": {
    "2025-12-01": 8,
    "2025-12-02": 8,
    "2025-12-03": 8,
    "2025-12-04": 8,
    "2025-12-05": 8,
    "2025-12-06": 0,
    "2025-12-07": 0,
    "2025-12-08": 0,
    "2025-12-09": 8,
    "2025-12-10": 8,
    "2025-12-11": 8,
    "2025-12-12": 8,
    "2025-12-13": 0,
    "2025-12-14": 0,
    "2025-12-15": 8,
    "2025-12-16": 8,
    "2025-12-17": 8,
    "2025-12-18": 8,
    "2025-12-19": 8,
    "2025-12-20": 0,
    "2025-12-21": 0,
    "2025-12-22": 8,
    "2025-12-23": 8,
    "2025-12-24": 8,
    "2025-12-25": 0,
    "2025-12-26": 0,
    "2025-12-27": 0,
    "2025-12-28": 0,
    "2025-12-29": 8,
    "2025-12-30": 8,
    "2025-12-31": 8
  },
  "bank_hours": "0.00",
  "time_entries": [
    {
      "id": 806,
      "date": "2025-12-01",
      "task": 16,
      "bank_to": "0.00",
      "comment": null,
      "bank_from": "0.00",
      "rest_hours": "0.00",
      "sick_hours": "0.00",
      "task_title": "Some task",
      "leave_hours": "0.00",
      "travel_hours": "0.00",
      "holiday_hours": "0.00",
      "last_modified": "2025-12-11T08:40:56.708222+00:00",
      "on_call_hours": "0.00",
      "day_shift_hours": "8.00",
      "protocol_number": null,
      "night_shift_hours": "0.00",
      "special_leave_hours": "0.00",
      "special_leave_reason": null
    },
    {
      "id": 807,
      "date": "2025-12-02",
      "task": 16,
      "bank_to": "0.00",
      "comment": null,
      "bank_from": "0.00",
      "rest_hours": "0.00",
      "sick_hours": "0.00",
      "task_title": "Some task",
      "leave_hours": "0.00",
      "travel_hours": "0.00",
      "holiday_hours": "0.00",
      "last_modified": "2025-12-11T08:40:56.745659+00:00",
      "on_call_hours": "0.00",
      "day_shift_hours": "8.00",
      "protocol_number": null,
      "night_shift_hours": "0.00",
      "special_leave_hours": "0.00",
      "special_leave_reason": null
    }
  ],
  "timesheet_colors": {
    "exact_schedule_color_dark_theme": "#3d3846",
    "exact_schedule_color_bright_theme": "#ffffff",
    "less_than_schedule_color_dark_theme": "#e01b24",
    "more_than_schedule_color_dark_theme": "#1a5fb4",
    "less_than_schedule_color_bright_theme": "#f66151",
    "more_than_schedule_color_bright_theme": "#99c1f1"
  }
}
"""
        submission = TimesheetSubmissionFactory.build(
            period=(_dt('2025-12-01'), _dt('2026-01-01')), timesheet=json.loads(timesheet_data)
        )
        days = Krm3Day.from_submission(submission)
        assert all(day.data_special_leave_reason is None for day in days)
