from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

from krm3.core.models import Resource, TimeEntry, User, TimesheetSubmission
from krm3.timesheet.dto import TimesheetDTO

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable


def get_resource_timesheet(
    end_date: datetime.date, resource: Resource, start_date: datetime.date, requestor: User
) -> TimesheetDTO:
    """Retrieve the resource timesheet for a specific date interval."""
    tms = TimesheetSubmission.objects.filter(
        resource=resource, period=[start_date, end_date + relativedelta(days=1)]
    ).first()

    if tms and tms.closed and tms.timesheet:
        return tms.timesheet

    return TimesheetDTO(requested_by=requestor).fetch(resource, start_date, end_date)


def verify_time_entries_from_same_day(time_entries: Iterable[TimeEntry]) -> None:
    """Check that all time entries belong to the same day, raise otherwise.

    :param time_entries: the time entries to check
    :raises ValueError: when not all time entries have the same `date`.
    """
    if len({entry.date for entry in time_entries}) > 1:
        raise ValueError('Time entries must belong to the same day.')


def worked_hours(time_entries: Iterable[TimeEntry]) -> Decimal:
    """Return the total of all the given time entries' task hours."""
    bank_from = sum(entry.bank_from or 0 for entry in time_entries)
    bank_to = sum(entry.bank_to or 0 for entry in time_entries)
    withdrawn_hours = max(0, bank_from - bank_to)
    return Decimal(sum(entry.total_task_hours for entry in time_entries)) + withdrawn_hours


def special_hours(time_entries: Iterable[TimeEntry]) -> Decimal:
    """Return the total of all the given time entries' special hours.

    See `TimeEntry.special_hours` for more details.
    """
    return Decimal(sum(entry.special_hours for entry in time_entries))


def regular_hours(time_entries: Iterable[TimeEntry], due_hours: Decimal) -> Decimal | None:
    """Return the "regular" work hours logged for the given time entries.

    Since this metric makes sense only if all given entries belong to the
    same day, a `ValueError` is raised if this is not true.

    Furthermore, when no work has been done, regular work hours are not
    allowed, and `None` is returned.

    :param time_entries: the time entries to use for the computation
    :param due_hours: the hours the resource is supposed to work
    :return: the total "regular" hours.
    """
    verify_time_entries_from_same_day(time_entries)

    return min(hours, due_hours) if (hours := worked_hours(time_entries)) else None


def overtime(time_entries: Iterable[TimeEntry], due_hours: Decimal) -> Decimal | None:
    """Return the overtime logged for the given time entries.

    Since overtime makes sense only if all given entries belong to the
    same day, a `ValueError` is raised if this is not true.

    Furthermore, when "special activities" are logged
    (see `TimeEntry.special_hours`), no overtime is allowed, and `None`
    is returned.

    Negative overtime values are clamped to 0.

    If an hours bank transaction is present, banked hours are subtracted
    from the grand total.

    :param time_entries: the time entries to use for the computation
    :param due_hours: the threshold for overtime
    :return: the overtime in hours, or `None` if overtime does not apply.
    """
    verify_time_entries_from_same_day(time_entries)

    if special_hours(time_entries) > 0:
        return None

    bank_from = sum(entry.bank_from or 0 for entry in time_entries)
    bank_to = sum(entry.bank_to or 0 for entry in time_entries)
    banked_hours = max(0, bank_to - bank_from)
    if (overtime := worked_hours(time_entries) - due_hours - banked_hours) > 0:
        return overtime
    return Decimal(0)
