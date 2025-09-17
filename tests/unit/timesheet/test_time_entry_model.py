import datetime
from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
from django.core import exceptions

from testutils.factories import (
    BasketFactory,
    InvoiceEntryFactory,
    ProjectFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TimeEntryFactory,
    TimesheetSubmissionFactory,
)

from krm3.core.models.timesheets import TimeEntry
from tests._extras.testutils.factories import ContractFactory


class TestBasket:
    def test_current_capacity_is_affected_exclusively_by_invoiced_entries(self):
        basket = BasketFactory(initial_capacity=1000)

        # invoiced hours should erode the capacity
        invoiced_hours = [200, 250, 125]
        for amt in invoiced_hours:
            InvoiceEntryFactory(basket=basket, amount=amt)
        capacity_after_invoices = basket.current_capacity()
        assert capacity_after_invoices == 425

        # any currently open task entries should NOT erode the capacity
        task = TaskFactory(basket_title=basket.title)
        for days in range(5):
            target_day = task.start_date + datetime.timedelta(days=days)
            TimeEntryFactory(date=target_day, task=task)
        capacity_after_invoices_and_time_entries = basket.current_capacity()
        assert capacity_after_invoices_and_time_entries == capacity_after_invoices

    def test_current_projected_capacity_is_affected_by_invoiced_entries_and_open_time_entries(self):
        basket = BasketFactory(initial_capacity=1000)

        # invoiced hours should erode the capacity
        invoiced_hours = [200, 250, 125]
        for amt in invoiced_hours:
            InvoiceEntryFactory(basket=basket, amount=amt)
        capacity_after_invoices = basket.current_projected_capacity()
        assert capacity_after_invoices == 425

        # any currently open time entries should also erode the capacity
        task = TaskFactory(basket_title=basket.title)
        for days in range(5):
            target_day = task.start_date + datetime.timedelta(days=days)
            # 40h in total
            TimeEntryFactory(date=target_day, task=task, resource=task.resource, day_shift_hours=8)
        capacity_after_invoices_and_open_time_entries = basket.current_projected_capacity()
        assert capacity_after_invoices_and_open_time_entries < capacity_after_invoices
        assert capacity_after_invoices_and_open_time_entries == 385

        # closed time entries should be considered invoiced and
        # as such should be ignored
        timesheet = TimesheetSubmissionFactory(resource=task.resource,
                                               period=(task.start_date, task.start_date + datetime.timedelta(days=10)))
        other_task = TaskFactory(basket_title=basket.title)
        for days in range(5):
            target_day = task.start_date + datetime.timedelta(days=days)
            # 40h in total
            TimeEntryFactory(
                date=target_day,
                task=other_task,
                resource=other_task.resource,
                day_shift_hours=8,
                timesheet=timesheet,
            )
        assert basket.current_projected_capacity() == capacity_after_invoices_and_open_time_entries


class TestTimeEntry:
    @pytest.mark.parametrize(
        ('hour_field', 'expected_behavior'),
        (
            pytest.param('sick_hours', does_not_raise(), id='sick'),
            pytest.param('holiday_hours', does_not_raise(), id='holiday'),
            pytest.param('leave_hours', does_not_raise(), id='leave'),
            pytest.param('special_leave_hours', does_not_raise(), id='special_leave'),
            pytest.param('on_call_hours', pytest.raises(exceptions.ValidationError), id='on_call'),
            pytest.param('night_shift_hours', pytest.raises(exceptions.ValidationError), id='night_shift'),
            pytest.param('travel_hours', pytest.raises(exceptions.ValidationError), id='travel'),
            pytest.param('rest_hours', does_not_raise(), id='rest'),
        ),
    )
    def test_day_entry_is_saved_only_with_sick_holiday_rest_or_leave_hours(self, hour_field, expected_behavior):
        with expected_behavior:
            entry = TimeEntryFactory(
                task=None,
                day_shift_hours=0,
                special_leave_reason=SpecialLeaveReasonFactory() if hour_field == 'special_leave_hours' else None,
                **{hour_field: 8},
            )
            # NOTE: asserting the obvious to appease Ruff :^)
            assert entry.task is None

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
    def test_rejects_negative_hours(self, hour_field):
        resource = ResourceFactory()
        time_logged = {'day_shift_hours': 0} | {hour_field: -1}
        with pytest.raises(exceptions.ValidationError):
            TimeEntryFactory(
                task=(
                    TaskFactory(
                        project=ProjectFactory(start_date=datetime.date(2020, 1, 1)),
                        resource=resource,
                        start_date=datetime.date(2020, 1, 1),
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
    def test_rejects_too_many_hours(self, hour_field):
        resource = ResourceFactory()
        time_logged = {'day_shift_hours': 0} | {hour_field: 25}
        with pytest.raises(exceptions.ValidationError):
            TimeEntryFactory(
                date=datetime.date(2024, 1, 1),
                task=(
                    TaskFactory(
                        project=ProjectFactory(start_date=datetime.date(2020, 1, 1)),
                        resource=resource,
                        start_date=datetime.date(2020, 1, 1),
                    )
                    if hour_field in ('day_shift_hours', 'night_shift_hours', 'travel_hours', 'on_call_hours')
                    else None
                ),
                special_leave_reason=SpecialLeaveReasonFactory() if hour_field == 'special_leave_hours' else None,
                **time_logged,
            )

    def test_rejects_too_many_day_shift_hours(self):
        project = ProjectFactory(start_date=datetime.date(2020, 1, 1))
        resource = ResourceFactory()
        with pytest.raises(exceptions.ValidationError):
            TimeEntryFactory(
                date=datetime.date(2024, 1, 1),
                resource=resource,
                task=TaskFactory(project=project, resource=resource, start_date=datetime.date(2020, 1, 1)),
                day_shift_hours=Decimal(16.25),
            )

    def test_rejects_too_many_night_shift_hours(self):
        project = ProjectFactory(start_date=datetime.date(2020, 1, 1))
        resource = ResourceFactory()
        with pytest.raises(exceptions.ValidationError):
            TimeEntryFactory(
                date=datetime.date(2024, 1, 1),
                resource=resource,
                task=TaskFactory(project=project, resource=resource, start_date=datetime.date(2020, 1, 1)),
                day_shift_hours=0,
                night_shift_hours=Decimal(8.25),
            )

    def test_rejects_both_bank_deposit_and_withdrawal_same_day(self):
        """Test that you cannot both deposit to and withdraw from bank on same day."""
        resource = ResourceFactory()
        with pytest.raises(exceptions.ValidationError,
                           match='Cannot both withdraw from and deposit to bank hours on the same day'):
            TimeEntryFactory(
                day_shift_hours=0,
                bank_from=2,
                bank_to=3,
                resource=resource,
            )

    def test_bank_hours_included_in_total_hours_calculation(self):
        """Test that bank hours are properly included in total_hours calculation."""
        project = ProjectFactory(start_date=datetime.date(2020, 1, 1))
        resource = ResourceFactory()
        entry1 = TimeEntryFactory(
            day_shift_hours=10,
            task=TaskFactory(project=project, resource=resource, start_date=datetime.date(2020, 1, 1)),
            resource=resource,
        )
        TimeEntryFactory(
            day_shift_hours=0,
            bank_to=2,
            date=entry1.date,
            resource=resource,
        )

        daily_entries = TimeEntry.objects.filter(
            resource=resource,
            date=entry1.date
        )
        total_day_hours_with_deposit = sum(entry.total_hours for entry in daily_entries)
        assert total_day_hours_with_deposit == 8

        entry2 = TimeEntryFactory(
            day_shift_hours=6,
            task=TaskFactory(project=project, resource=resource),
            resource=resource,
            date=datetime.date(2020, 3, 4)
        )
        TimeEntryFactory(
            day_shift_hours=0,
            bank_from=2,
            date=entry2.date,
            resource=resource,
        )
        daily_entries = TimeEntry.objects.filter(
            resource=resource,
            date=entry2.date
        )
        total_day_hours_with_withdrawal = sum(entry.total_hours for entry in daily_entries)
        assert total_day_hours_with_withdrawal == 8

    def test_bank_hours_with_day_entry(self):
        """Test that bank hours can be used with day entries (non-task)."""
        resource = ResourceFactory()

        entry = TimeEntryFactory(
            task=None,
            resource=resource,
            date = datetime.date(2025,8,20),
            day_shift_hours=0,
            leave_hours=3,
            bank_from=2,
            bank_to=0,
        )
        assert entry.total_hours == 5

    def test_rejects_bank_deposit_exceeding_upper_limit(self):
        """Test that bank deposit is rejected if it would exceed upper balance limit."""
        project = ProjectFactory()
        resource = ResourceFactory()
        task = TaskFactory(project=project, resource=resource)
        TimeEntryFactory(
            date=datetime.date(2025, 1, 2),
            resource=resource,
            task=task,
            day_shift_hours=16,
        )
        TimeEntryFactory(
            date = datetime.date(2025, 1, 3),
            resource=resource,
            task=task,
            day_shift_hours=16,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 1, 10),
            resource=resource,
            task=task,
            day_shift_hours=10,
        )
        TimeEntryFactory(
            date = datetime.date(2025, 1, 2),
            resource=resource,
            day_shift_hours=0,
            bank_to=8,
        )
        TimeEntryFactory(
            date = datetime.date(2025, 1, 3),
            resource=resource,
            day_shift_hours=0,
            bank_to=8,
        )

        with pytest.raises(exceptions.ValidationError, match='This transaction would exceed the maximum bank balance'):
            TimeEntryFactory(
                date=datetime.date(2025, 1, 10),
                resource=resource,
                day_shift_hours=0,
                bank_to=2,
            )

    def test_rejects_bank_deposit_exceeding_lower_limit(self):
        """Test that bank deposit is rejected if it would exceed upper balance limit."""
        project = ProjectFactory()
        resource = ResourceFactory()
        task = TaskFactory(project=project, resource=resource)
        TimeEntryFactory(
            date=datetime.date(2024, 1, 2),
            resource=resource,
            task=task,
            day_shift_hours=2,
            bank_from=8,
        )
        TimeEntryFactory(
            date=datetime.date(2024, 1, 3),
            resource=resource,
            task=task,
            day_shift_hours=4,
            bank_from=4,
        )

        with pytest.raises(exceptions.ValidationError, match='This transaction would exceed the minimum bank balance'):
            TimeEntryFactory(
                resource=resource,
                task=task,
                day_shift_hours=2,
                bank_from=6,
            )

    def test_reject_task_entry_deletion_when_deposited_hours(self):
        project = ProjectFactory()
        resource = ResourceFactory()
        task = TaskFactory(project=project, resource=resource)
        time_entry = TimeEntryFactory(
            date=datetime.date(2024, 1, 2),
            resource=resource,
            task=task,
            day_shift_hours=10,
        )
        TimeEntryFactory(
            date=datetime.date(2024, 1, 2),
            resource=resource,
            day_shift_hours=0,
            bank_to=2,
        )
        with pytest.raises(exceptions.ValidationError, match='Cannot delete this time entry. Removing it would cause '
                                                             'negative work hours'):
            time_entry.delete()

    def test_holiday_rejects_any_bank_transactions(self):
        """Test that holiday entries cannot have any bank transactions."""
        resource = ResourceFactory()

        with pytest.raises(exceptions.ValidationError, match='Cannot use bank hours during holidays'):
            TimeEntryFactory(
                task=None,
                resource=resource,
                day_shift_hours=0,
                holiday_hours=8,
                bank_to=2,
                bank_from=0,
            )

        with pytest.raises(exceptions.ValidationError, match='Cannot use bank hours during holidays'):
            TimeEntryFactory(
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
    def test_day_entries_reject_bank_deposits(self, day_entry_field):
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
            TimeEntryFactory(**kwargs)

    def test_bank_hours_with_scheduled_hours(self):
        resource = ResourceFactory()
        project = ProjectFactory()
        task = TaskFactory(project=project, resource=resource)
        date = datetime.date(2025, 1, 14)
        TimeEntryFactory(
            date=date,
            resource=resource,
            task=task,
            day_shift_hours=6,
        )
        time_deposit = TimeEntryFactory.build(task=None,resource=resource,date=date,day_shift_hours=0,bank_to=2)

        with pytest.raises(exceptions.ValidationError, match='Cannot deposit 2 bank hours'):
            time_deposit.save()

        time_withdraw = TimeEntryFactory.build(task=None, resource=resource, date=date, day_shift_hours=0, bank_from=5)
        with pytest.raises(exceptions.ValidationError, match='Cannot withdraw bank hours when task hours'):
            time_withdraw.save()


    def test_bank_deposit_success_with_correct_custom_schedule(self):
        start_dt = datetime.date(2020, 1, 1)
        end_dt = datetime.date(2026, 1, 1)
        contract = ContractFactory(
            period=(start_dt, end_dt),
            working_schedule={'fri': 3, 'mon': 3, 'sat': 0, 'sun': 0, 'thu': 3, 'tue': 3, 'wed': 3}
        )
        project = ProjectFactory()
        resource = contract.resource
        task = TaskFactory(project=project, resource=resource)
        date = datetime.date(2025, 1, 14)
        TimeEntryFactory(
            date=date,
            resource=resource,
            task=task,
            day_shift_hours=4,
        )
        time_deposit = TimeEntryFactory(task=None, resource=resource, date=date, day_shift_hours=0, bank_to=1)

        assert time_deposit.bank_to == 1

    def test_bank_deposit_with_0_scheduled_hours(self):
        resource = ResourceFactory()
        date = datetime.date(2025, 8, 2)
        with does_not_raise():
            TimeEntryFactory(
                resource=resource,
                date=date,
                bank_to=3,
                day_shift_hours=0,
            )

    def test_is_saved_without_hours_logged(self):
        """Valid edge case: 0 total hours on a task."""
        task = TaskFactory()
        entry = TimeEntryFactory(day_shift_hours=8, task=task, resource=task.resource)
        entry.day_shift_hours = 0
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.day_shift_hours == 0

    def test_is_saved_with_all_task_entry_hours_filled(self):
        """Non-zero total hours on a task, all non-full-day non-task hours fields filled"""
        task = TaskFactory()
        entry = TimeEntryFactory(day_shift_hours=8, task=task, resource=task.resource)
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

    _day_entry_fields = ('sick_hours', 'holiday_hours', 'leave_hours', 'rest_hours', 'special_leave_hours')

    @pytest.mark.parametrize('existing_hours_field', _day_entry_fields)
    @pytest.mark.parametrize('new_hours_field', _day_entry_fields)
    def test_day_entry_overwrites_other_existing_day_entry_on_the_same_day(self, existing_hours_field, new_hours_field):
        resource = ResourceFactory()
        absence_day = datetime.date(2024, 1, 1)
        _absence_entry = TimeEntryFactory(
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
            _absence_entry_on_other_day = TimeEntryFactory(
                date=datetime.date(2024, 1, 2),
                day_shift_hours=0,
                resource=resource,
                special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
                **{new_hours_field: 8},
            )

            # another resource should be able to log their own absence
            # entry on the same day...
            other_resource = ResourceFactory()
            _absence_entry_for_other_resource = TimeEntryFactory(
                date=absence_day,
                day_shift_hours=0,
                resource=other_resource,
                special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
                **{new_hours_field: 8},
            )

        _new_entry = TimeEntryFactory(
            date=absence_day,
            day_shift_hours=0,
            resource=resource,
            special_leave_reason=SpecialLeaveReasonFactory() if new_hours_field == 'special_leave_hours' else None,
            **{new_hours_field: 8},
        )
        day_entries = TimeEntry.objects.day_entries().filter(date=absence_day, resource=resource)  # pyright: ignore
        assert day_entries.count() == 1
        assert getattr(day_entries.get(), new_hours_field) == 8

    _task_entry_fields = ('day_shift_hours', 'travel_hours', 'night_shift_hours', 'on_call_hours')

    @pytest.mark.parametrize('field', _task_entry_fields)
    def test_task_entry_is_saved_only_when_no_other_task_entry_exists_on_the_same_day_for_the_same_task(self, field):
        resource = ResourceFactory()
        project = ProjectFactory()
        task = TaskFactory(title='whoops', project=project, start_date=project.start_date, resource=resource)
        other_task = TaskFactory(title='good', project=project, start_date=project.start_date, resource=resource)
        work_day = datetime.date(2024, 1, 1)

        def _make_time_entry(**kwargs):
            factory_kwargs = {'date': work_day, 'task': task, 'resource': resource, 'day_shift_hours': 0} | kwargs
            return TimeEntryFactory(**factory_kwargs)

        _existing_time_entry = _make_time_entry(day_shift_hours=2)

        # the resource should be able to log their time for another
        # available day on the same task
        _new_time_entry_on_other_day = _make_time_entry(date=datetime.date(2024, 1, 2), task=other_task, **{field: 2})
        assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 1  # pyright: ignore

        # the resource should be able to log their time for the same
        # day on another available task
        _new_time_entry_on_other_task = _make_time_entry(task=other_task, **{field: 6})
        assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 2  # pyright: ignore

        _overwriting_entry = _make_time_entry(**{field: 2})
        assert TimeEntry.objects.task_entries().filter(date=work_day, resource=resource).count() == 2  # pyright: ignore

    def test_is_saved_as_sick_day(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
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

    def test_is_saved_as_holiday(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
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

    def test_is_saved_as_leave(self):
        """Leave hours with no work or task-related hours logged"""
        entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
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

    def test_is_saved_as_special_leave(self):
        """Special leave hours with no work or task-related hours logged"""
        entry = TimeEntryFactory(day_shift_hours=8, task=TaskFactory())
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

    def test_raises_if_more_than_one_absence_fields_is_filled(self):
        entry = TimeEntryFactory(day_shift_hours=0)
        entry.sick_hours = 4
        entry.holiday_hours = 4
        entry.leave_hours = 1
        with pytest.raises(exceptions.ValidationError, match='more than one kind of non-task hours in a day'):
            entry.save()

    def test_raises_if_logging_work_during_sick_days(self):
        entry = TimeEntryFactory(day_shift_hours=4, task=TaskFactory())
        entry.sick_hours = 4
        with pytest.raises(exceptions.ValidationError, match='task hours and non-task hours together'):
            entry.save()

    def test_raises_if_logging_work_during_holidays(self):
        entry = TimeEntryFactory(day_shift_hours=4, task=TaskFactory())
        entry.holiday_hours = 4
        with pytest.raises(exceptions.ValidationError, match='task hours and non-task hours together'):
            entry.save()

    @pytest.mark.parametrize(
        ('hours_key', 'expected_to_raise'),
        (
            pytest.param('day_shift_hours', does_not_raise(), id='day'),
            pytest.param('night_shift_hours', does_not_raise(), id='night'),
            pytest.param('rest_hours', does_not_raise(), id='rest'),
            pytest.param('travel_hours', does_not_raise(), id='travel'),
            pytest.param('on_call_hours', does_not_raise(), id='on_call'),
            pytest.param(
                'sick_hours', pytest.raises(exceptions.ValidationError, match='Comment is mandatory'), id='sick'
            ),
            pytest.param('holiday_hours', does_not_raise(), id='holiday'),
            pytest.param('leave_hours', does_not_raise(), id='leave'),
            pytest.param('special_leave_hours', does_not_raise(), id='leave'),
        ),
    )
    def test_raises_if_missing_mandatory_comment(self, hours_key, expected_to_raise):
        hours = {'day_shift_hours': 0} | {hours_key: 8}
        reason = SpecialLeaveReasonFactory() if hours_key == 'special_leave_hours' else None
        with expected_to_raise:
            TimeEntryFactory(
                task=(
                    None
                    if str(hours_key).removesuffix('_hours') in ('sick', 'holiday', 'rest', 'leave', 'special_leave')
                    else TaskFactory()
                ),
                comment=None,
                special_leave_reason=reason,
                **hours,
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
    def test_raises_if_special_leave_reason_not_on_special_leave_entry(self, hours_key, expected_to_raise):
        hours = {'day_shift_hours': 0} | {hours_key: 8}
        reason = SpecialLeaveReasonFactory()
        with expected_to_raise:
            TimeEntryFactory(
                task=(
                    None
                    if str(hours_key).removesuffix('_hours') in ('sick', 'holiday', 'leave', 'special_leave')
                    else TaskFactory()
                ),
                special_leave_reason=reason,
                **hours,
            )

    def test_raises_if_special_leave_has_invalid_reason(self):
        valid_reason = SpecialLeaveReasonFactory(title='valid')

        with does_not_raise():
            entry = TimeEntryFactory(
                date=datetime.date(2024, 1, 1),
                day_shift_hours=0,
                special_leave_hours=2,
                special_leave_reason=valid_reason,
            )

        expired_reason = SpecialLeaveReasonFactory(title='expired', to_date=datetime.date(2020, 1, 1))
        entry.special_leave_reason = expired_reason
        with pytest.raises(exceptions.ValidationError, match='Reason "expired" is not valid'):
            entry.save()

        upcoming_reason = SpecialLeaveReasonFactory(title='upcoming', from_date=datetime.date(2025, 1, 1))
        entry.special_leave_reason = upcoming_reason
        with pytest.raises(exceptions.ValidationError, match='Reason "upcoming" is not valid'):
            entry.save()

    def test_raises_if_ends_before_starting(self):
        with does_not_raise():
            # edge case: one day long special leave reason
            _valid = SpecialLeaveReasonFactory(from_date=datetime.date(2024, 1, 1), to_date=datetime.date(2024, 1, 1))

        with pytest.raises(exceptions.ValidationError, match='must not be later'):
            _should_fail = SpecialLeaveReasonFactory(
                from_date=datetime.date(2024, 1, 1), to_date=datetime.date(2020, 1, 1)
            )

    @pytest.mark.parametrize('time_entry_date, expected_assigned_timesheet_index',
                             [
                                 (datetime.date(2020, 5, 15), 0),
                                 (datetime.date(2020, 6, 15), 1),
                                 (datetime.date(2020, 7, 15), 2),
                                 (datetime.date(2020, 5, 31), 0),
                                 (datetime.date(2020, 6, 1), 1),
                                 (datetime.date(2020, 8, 15), None),
                                 (datetime.date(2020, 4, 15), None),
                             ])
    def test_time_entry_should_be_assigned_to_appropriate_timesheet(
            self, time_entry_date, expected_assigned_timesheet_index):
        resource = ResourceFactory()
        task = TaskFactory()
        TimeEntryFactory(date=time_entry_date, resource=resource, task=task)

        timesheets = []

        timesheets.append(TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 5, 1), datetime.date(2020, 6, 1))
        ))
        timesheets.append(TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 6, 1), datetime.date(2020, 7, 1))
        ))
        timesheets.append(TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 7, 1), datetime.date(2020, 8, 1))
        ))

        for i, timesheet in enumerate(timesheets):
            expected_count = 1 if i == expected_assigned_timesheet_index else 0
            assert timesheet.timeentry_set.count() == expected_count

    def test_deleting_timesheet_should_set_key_to_none(self):
        resource = ResourceFactory()
        task = TaskFactory()
        time_entry = TimeEntryFactory(date=datetime.date(2020, 5, 15), resource=resource, task=task)

        timesheet = TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 5, 1), datetime.date(2020, 6, 1))
        )

        time_entry.refresh_from_db()
        assert timesheet.timeentry_set.count() == 1
        assert time_entry.timesheet == timesheet
        timesheet.delete()
        time_entry.refresh_from_db()
        assert time_entry.timesheet is None

    def updating_timeentry_date_should_update_assigned_timesheet(self):
        resource = ResourceFactory()
        task = TaskFactory()
        time_entry = TimeEntryFactory(date=datetime.date(2020, 5, 15), resource=resource, task=task)
        timesheet_1 = TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 5, 1), datetime.date(2020, 6, 1))
        )
        timesheet_2 = TimesheetSubmissionFactory(
            resource=resource,
            closed=True,
            period=(datetime.date(2020, 6, 1), datetime.date(2020, 6, 1))
        )
        assert time_entry.timesheet == timesheet_1
        time_entry.date = datetime.date(2020, 6, 15)
        time_entry.save()
        assert time_entry.timesheet == timesheet_2
