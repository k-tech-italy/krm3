import datetime

from django.core import exceptions
import pytest

from factories import InvoiceEntryFactory, TimeEntryFactory, TaskFactory, BasketFactory
from krm3.timesheet.models import TimeEntryState


class TestBasket:
    def test_current_capacity_is_affected_exclusively_by_invoiced_entries(
        self
    ):
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
            TimeEntryFactory(date=task.start_date + datetime.timedelta(days=days), task=task)
        capacity_after_invoices_and_time_entries = basket.current_capacity()
        assert capacity_after_invoices_and_time_entries == capacity_after_invoices

    def test_current_projected_capacity_is_affected_by_invoiced_entries_and_open_time_entries(
        self
    ):
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
            # 40h in total
            TimeEntryFactory(date=task.start_date + datetime.timedelta(days=days), task=task, work_hours=8)
        capacity_after_invoices_and_open_time_entries = basket.current_projected_capacity()
        assert capacity_after_invoices_and_open_time_entries < capacity_after_invoices
        assert capacity_after_invoices_and_open_time_entries == 385

        # closed time entries should be considered invoiced and
        # as such should be ignored
        for days in range(5):
            # 40h in total
            TimeEntryFactory(
                date=task.start_date + datetime.timedelta(days=days),
                task=task,
                work_hours=8,
                state=TimeEntryState.CLOSED,
            )
        assert basket.current_projected_capacity() == capacity_after_invoices_and_open_time_entries


class TestTimeEntry:
    # validations on the hours logged
    # we should be able to save a time entry if only one of the following occurs:
    # - we logged hours on non-full-day absence fields (e.g. work, leave, rest)
    # - we logged sick hours
    # - we logged holiday hours

    def test_is_saved_without_hours_logged(self):
        """Valid edge case: 0 total hours on a task."""
        entry = TimeEntryFactory(work_hours=8)
        entry.work_hours = 0
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0

    def test_is_saved_with_all_non_full_day_absence_hours_filled(self):
        """Non-zero total hours on a task, all non-full-day absence fields filled"""
        entry = TimeEntryFactory(work_hours=8)
        entry.leave_hours = 1
        entry.overtime_hours = 1
        entry.on_call_hours = 2
        entry.rest_hours = 1.5
        entry.travel_hours = 1
        entry.work_hours = 4.5
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.leave_hours + entry.rest_hours + entry.travel_hours + entry.work_hours == 8
        assert entry.overtime_hours == 1
        assert entry.on_call_hours == 2

    def test_is_saved_as_sick_day(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(work_hours=8)
        entry.work_hours = 0
        entry.sick_hours = 8
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0
        assert entry.sick_hours == 8

    def test_is_saved_as_holiday(self):
        """Sick day with no work or task-related hours logged"""
        entry = TimeEntryFactory(work_hours=8)
        entry.work_hours = 0
        entry.holiday_hours = 8
        entry.save()
        # NOTE: asserting the obvious to appease Ruff :^)
        entry.refresh_from_db()
        assert entry.work_hours == 0
        assert entry.holiday_hours == 8

    def test_raises_if_more_than_one_full_day_absence_fields_is_filled(self):
        entry = TimeEntryFactory(work_hours=0)
        entry.sick_hours = 4
        entry.holiday_hours = 4
        with pytest.raises(
            exceptions.ValidationError, match='You cannot log more than one type of full-day absences in a day.'
        ):
            entry.save()

    def test_raises_if_logging_work_during_sick_days(self):
        entry = TimeEntryFactory(work_hours=4)
        entry.sick_hours = 4
        with pytest.raises(exceptions.ValidationError, match='You cannot log work-related hours on a sick day.'):
            entry.save()

    def test_raises_if_logging_work_during_holidays(self):
        entry = TimeEntryFactory(work_hours=4)
        entry.holiday_hours = 4
        with pytest.raises(exceptions.ValidationError, match='You cannot log work-related hours on a holiday.'):
            entry.save()
