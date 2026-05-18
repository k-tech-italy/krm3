import datetime

from krm3.core.models import Contract
from krm3.utils.dates import KrmDay
from testutils.date_utils import _dt
from testutils.factories import (
    BasketFactory,
    InvoiceEntryFactory,
    TaskFactory,
    TaskEntryFactory,
    TimesheetSubmissionFactory, POFactory, DayEntryFactory,
)

def test_current_capacity_is_affected_exclusively_by_invoiced_entries():
    basket = BasketFactory(initial_capacity=1000)

    # invoiced hours should erode the capacity
    invoiced_hours = [200, 250, 125]
    for amt in invoiced_hours:
        InvoiceEntryFactory(basket=basket, amount=amt)
    capacity_after_invoices = basket.current_capacity()
    assert capacity_after_invoices == 425

    # any currently open task entries should NOT erode the capacity
    task = TaskFactory(basket_title=basket.title, contract=True)
    for days in range(5):
        target_day = (KrmDay(task.period.lower) + days).date
        day_entry = DayEntryFactory(day=target_day, resource=task.resource)
        TaskEntryFactory(day_entry=day_entry, task=task)
    capacity_after_invoices_and_time_entries = basket.current_capacity()
    assert capacity_after_invoices_and_time_entries == capacity_after_invoices

def test_current_projected_capacity_is_affected_by_invoiced_entries_and_open_time_entries():
    basket = BasketFactory(initial_capacity=1000)

    # invoiced hours should erode the capacity
    invoiced_hours = [200, 250, 125]
    for amt in invoiced_hours:
        InvoiceEntryFactory(basket=basket, amount=amt)
    capacity_after_invoices = basket.current_projected_capacity()
    assert capacity_after_invoices == 425

    # any currently open time entries should also erode the capacity
    task = TaskFactory(period=('20190101', None), basket_title=basket.title, contract=True)

    contract = Contract.objects.first()
    for days in range(5):
        target_day = (KrmDay(task.period.lower) + days).date
        day_entry = DayEntryFactory(day=target_day, resource=task.resource, contract=contract)
        # 40h in total
        TaskEntryFactory(day_entry=day_entry, task=task, resource=task.resource, day_shift_hours=8)
    capacity_after_invoices_and_open_time_entries = basket.current_projected_capacity()
    assert capacity_after_invoices_and_open_time_entries < capacity_after_invoices
    assert capacity_after_invoices_and_open_time_entries == 385

    # closed time entries should be considered invoiced and
    # as such should be ignored
    timesheet = TimesheetSubmissionFactory(
        resource=task.resource, period=(task.period.lower, (KrmDay(task.period.lower) + 10).date)
    )
    other_task = TaskFactory(basket_title=basket.title)
    for days in range(5):
        target_day = (KrmDay(task.period.lower) + days).date
        day_entry = DayEntryFactory(day=target_day, resource=task.resource)
        # 40h in total
        TaskEntryFactory(
            day_entry=day_entry,
            task=other_task,
            resource=other_task.resource,
            day_shift_hours=8,
            timesheet=timesheet,
        )
    assert basket.current_projected_capacity() == capacity_after_invoices_and_open_time_entries
