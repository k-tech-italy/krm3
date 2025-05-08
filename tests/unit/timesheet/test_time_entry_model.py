import datetime
from contextlib import nullcontext as does_not_raise

from django.core import exceptions
import pytest

from testutils.factories import InvoiceEntryFactory, TimeEntryFactory, TaskFactory, BasketFactory, ResourceFactory
from krm3.core.models import TimeEntryState


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
            TimeEntryFactory(date=target_day.date(), task=task)
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
            TimeEntryFactory(date=target_day.date(), task=task, resource=task.resource, work_hours=8)
        capacity_after_invoices_and_open_time_entries = basket.current_projected_capacity()
        assert capacity_after_invoices_and_open_time_entries < capacity_after_invoices
        assert capacity_after_invoices_and_open_time_entries == 385

        # closed time entries should be considered invoiced and
        # as such should be ignored
        other_task = TaskFactory(basket_title=basket.title)
        for days in range(5):
            target_day = task.start_date + datetime.timedelta(days=days)
            # 40h in total
            TimeEntryFactory(
                date=target_day.date(),
                task=other_task,
                resource=other_task.resource,
                work_hours=8,
                state=TimeEntryState.CLOSED,
            )
        assert basket.current_projected_capacity() == capacity_after_invoices_and_open_time_entries


class TestTimeEntry:
    @pytest.mark.parametrize(
        ('hour_field', 'expected_behavior'),
        (
            pytest.param('sick_hours', does_not_raise(), id='sick'),
            pytest.param('holiday_hours', does_not_raise(), id='holiday'),
            pytest.param('leave_hours', does_not_raise(), id='leave'),
            pytest.param('on_call_hours', pytest.raises(exceptions.ValidationError), id='on_call'),
            pytest.param('overtime_hours', pytest.raises(exceptions.ValidationError), id='overtime'),
            pytest.param('travel_hours', pytest.raises(exceptions.ValidationError), id='travel'),
            pytest.param('rest_hours', pytest.raises(exceptions.ValidationError), id='rest'),
        ),
    )
    def test_day_entry_is_saved_only_with_sick_holiday_or_leave_hours(self, hour_field, expected_behavior):
        with expected_behavior:
            entry = TimeEntryFactory(task=None, work_hours=0, **{hour_field: 8})
            # NOTE: asserting the obvious to appease Ruff :^)
            assert entry.task is None

    def test_is_saved_without_hours_logged(self):
        """Valid edge case: 0 total hours on a task."""
        task = TaskFactory()
        entry = TimeEntryFactory(work_hours=8, task=task, resource=task.resource)
        entry.work_hours = 0
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0

    def test_is_saved_with_all_task_entry_hours_filled(self):
        """Non-zero total hours on a task, all non-full-day absence fields filled"""
        task = TaskFactory()
        entry = TimeEntryFactory(work_hours=8, task=task, resource=task.resource)
        entry.overtime_hours = 1
        entry.on_call_hours = 2
        entry.rest_hours = 1.5
        entry.travel_hours = 1
        entry.work_hours = 5.5
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.rest_hours + entry.travel_hours + entry.work_hours == 8
        assert entry.overtime_hours == 1
        assert entry.on_call_hours == 2

    _day_entry_fields = ('sick_hours', 'holiday_hours', 'leave_hours')

    @pytest.mark.parametrize('existing_hours_field', _day_entry_fields)
    @pytest.mark.parametrize('new_hours_field', _day_entry_fields)
    def test_day_entry_is_saved_only_when_no_other_day_entry_exists_on_the_same_day(
        self, existing_hours_field, new_hours_field
    ):
        resource = ResourceFactory()
        absence_day = datetime.date(2024, 1, 1)
        _absence_entry = TimeEntryFactory(
            date=absence_day, work_hours=0, **{existing_hours_field: 8}, resource=resource
        )

        with does_not_raise():
            # the same resource should be able to log their absence on
            # a different available day
            _absence_entry_on_other_day = TimeEntryFactory(
                date=datetime.date(2024, 1, 2), work_hours=0, **{new_hours_field: 8}, resource=resource
            )

            # another resource should be able to log their own absence
            # entry on the same day...
            other_resource = ResourceFactory()
            _absence_entry_for_other_resource = TimeEntryFactory(
                date=absence_day, work_hours=0, **{new_hours_field: 8}, resource=other_resource
            )

        # ... but the same resource should not be able to log more than
        # one absence entry
        with pytest.raises(exceptions.ValidationError, match='already has a day entry'):
            TimeEntryFactory(date=absence_day, work_hours=0, **{new_hours_field: 0}, resource=resource)

    _task_entry_fields = ('work_hours', 'rest_hours', 'travel_hours', 'overtime_hours', 'on_call_hours')

    @pytest.mark.parametrize('field', _task_entry_fields)
    def test_task_entry_is_saved_only_when_no_other_task_entry_exists_on_the_same_day_for_the_same_task(self, field):
        resource = ResourceFactory()
        task = TaskFactory(title='whoops', resource=resource)
        other_task = TaskFactory(title='good', resource=resource)
        work_day = datetime.date(2024, 1, 1)
        _existing_time_entry = TimeEntryFactory(date=work_day, task=task, resource=resource, work_hours=2)

        with does_not_raise():
            # the resource should be able to log their time for another
            # available day on the same task
            _new_time_entry_on_other_day = TimeEntryFactory(
                date=datetime.date(2024, 1, 2), task=other_task, resource=resource, **{field: 2}
            )

            # the resource should be able to log their time for the same
            # day on another available task
            _new_time_entry_on_other_task = TimeEntryFactory(
                date=work_day, task=other_task, resource=resource, **{field: 6}
            )
        with pytest.raises(exceptions.ValidationError, match='already has a time entry'):
            TimeEntryFactory(date=work_day, task=task, resource=resource, **{field: 2})

    def test_is_saved_as_sick_day(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(work_hours=8, task=TaskFactory())
        entry.work_hours = 0
        entry.sick_hours = 8

        with pytest.raises(exceptions.ValidationError, match='absence in a task entry'):
            entry.save()

        entry.task = None
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0
        assert entry.sick_hours == 8

    def test_is_saved_as_holiday(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(work_hours=8, task=TaskFactory())
        entry.work_hours = 0
        entry.holiday_hours = 8

        with pytest.raises(exceptions.ValidationError, match='absence in a task entry'):
            entry.save()

        entry.task = None
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0
        assert entry.holiday_hours == 8

    def test_is_saved_as_leave(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(work_hours=8, task=TaskFactory())
        entry.work_hours = 0
        entry.leave_hours = 8

        with pytest.raises(exceptions.ValidationError, match='absence in a task entry'):
            entry.save()

        entry.task = None
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0
        assert entry.leave_hours == 8

    def test_raises_if_more_than_one_absence_fields_is_filled(self):
        entry = TimeEntryFactory(work_hours=0)
        entry.sick_hours = 4
        entry.holiday_hours = 4
        entry.leave_hours = 1
        with pytest.raises(exceptions.ValidationError, match='more than one kind of absence in a day'):
            entry.save()

    def test_raises_if_logging_work_during_sick_days(self):
        entry = TimeEntryFactory(work_hours=4, task=TaskFactory())
        entry.sick_hours = 4
        with pytest.raises(exceptions.ValidationError, match='task hours and absence hours together'):
            entry.save()

    def test_raises_if_logging_work_during_holidays(self):
        entry = TimeEntryFactory(work_hours=4, task=TaskFactory())
        entry.holiday_hours = 4
        with pytest.raises(exceptions.ValidationError, match='task hours and absence hours together'):
            entry.save()
