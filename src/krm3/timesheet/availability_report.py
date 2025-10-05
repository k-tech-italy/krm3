import datetime
import typing
from decimal import Decimal as D  # noqa: N817
from django.db.models import Q
from krm3.core.models import TimeEntry, Resource
from krm3.utils.dates import KrmDay
from dateutil.relativedelta import relativedelta


def timesheet_report_raw_data(
    from_date: datetime.date, to_date: datetime.date, project: str | None = None
) -> dict['Resource', dict[str, list[D]]]:
    qs = TimeEntry.objects.filter(
        Q(date__gte=from_date)
        & Q(date__lte=to_date)
        & Q(resource__active=True)
        & (Q(holiday_hours__gt=0) | Q(leave_hours__gt=0) | Q(special_leave_hours__gt=0))
    )

    if project is not None:
        qs = qs.filter(resource__task__project=project)

    qs = qs.order_by('resource', 'date')

    start_date = KrmDay(from_date)
    days_interval = (to_date - from_date).days + 1
    if project is not None:
        resources = Resource.objects.filter(task__project=project)
    else:
        resources = Resource.objects.all()
    results = {resource: {} for resource in resources}

    for value in results.values():
        value['absences'] = [*[None] * days_interval]

    for entry in qs:
        date = KrmDay(entry.date)
        index = date - start_date
        if entry.holiday_hours > 0:
            results[entry.resource]['absences'][index] = 'H'
        elif entry.leave_hours > 0 or entry.special_leave_hours > 0:
            results[entry.resource]['absences'][index] = f'L {entry.leave_hours + entry.special_leave_hours}'

    return results


def availability_report_data(current_month: str | None, project: str | None = '') -> dict[str, typing.Any]:
    """Prepare the data for the timesheet report."""
    if project == '':
        project = None
    if current_month is None:
        start_of_month = datetime.date.today().replace(day=1)
    else:
        start_of_month = datetime.datetime.strptime(current_month, '%Y%m').date()
    prev_month = start_of_month - relativedelta(months=1)
    next_month = start_of_month + relativedelta(months=1)

    end_of_month = start_of_month + relativedelta(months=1, days=-1)
    data = timesheet_report_raw_data(start_of_month, end_of_month, project)
    days = list(KrmDay(start_of_month.strftime('%Y-%m-%d')).range_to(end_of_month))

    return {
        'prev_month': prev_month.strftime('%Y%m'),
        'current_month': start_of_month.strftime('%Y%m'),
        'next_month': next_month.strftime('%Y%m'),
        'title': f'Availability {start_of_month.strftime("%B %Y")}',
        'days': days,
        'data': data,
    }
