import datetime
import typing
from django.contrib.auth import get_user_model
from decimal import Decimal as D  # noqa: N817

from dateutil.relativedelta import relativedelta

from krm3.core.models import TimeEntry, Resource, Task

from krm3.utils.dates import KrmDay, KrmCalendar

from krm3.utils.tools import format_data

from django.db.models import Q

User = get_user_model()

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

timeentry_key_mapping = {
    'night_shift_hours': 'Notturni',
    'on_call_hours': 'Reperibilità',
    'travel_hours': 'Ore Trasferta',
}


def _initialize_report_data(tasks: typing.Iterable[Task], days_interval: int) -> dict:
    """Initialize the results dictionary with tasks and default values."""
    results = {}
    for task in tasks:
        if task.resource not in results:
            results[task.resource] = {
                'Tot per Giorno': [D('0.00')] * (days_interval + 2),
                **{label: [D('0.00')] * (days_interval + 2) for label in timeentry_key_mapping.values()},
                'Assenze': [D('0.00')] * (days_interval + 2),
                'NUM GIORNI': 0,
            }
        results[task.resource][task] = [D('0.00')] * (days_interval + 2)

    return results


def _calculate_work_days_for_resources(
    results: dict,
    tasks: 'QuerySet[Task]',
    from_date: datetime.date,
    to_date: datetime.date,
) -> None:
    """Calculate NUM GIORNI and TOT HH for each resource."""
    calendar = KrmCalendar()
    work_days = calendar.get_work_days(from_date, to_date)
    for resource, data in results.items():
        owned_tasks = tasks.filter(resource=resource)
        work_days_without_task = [*work_days]
        for task in owned_tasks:
            work_days_without_task = [
                day
                for day in work_days_without_task
                if not (task.start_date <= day.date and (task.end_date is None or day.date <= task.end_date))
            ]

        data['NUM GIORNI'] = len(work_days) - len(work_days_without_task)
        data['TOT HH'] = data['NUM GIORNI'] * 8

def _handles_leaves(entry: TimeEntry, resource_data: dict, index: int | KrmDay) -> None:
    """Handle leaves and special leaves."""
    if isinstance(resource_data['Assenze'][index], D):
        if entry.leave_hours > 0:
            resource_data['Assenze'][index] += entry.leave_hours
            resource_data['Assenze'][1] += entry.leave_hours
        if entry.special_leave_hours > 0:
            resource_data['Assenze'][index] += entry.special_leave_hours
            resource_data['Assenze'][1] += entry.special_leave_hours



def _process_time_entries(results: dict, entries: 'QuerySet[TimeEntry]', start_date: KrmDay) -> None:
    """Process time entries and populates the results dictionary."""
    for entry in entries:

        resource_data = results[entry.resource]
        date = KrmDay(entry.date)
        index = date - start_date + 2

        if entry.task:
            total_hours = entry.day_shift_hours + entry.night_shift_hours + entry.travel_hours
            resource_data[entry.task][1] += total_hours
            resource_data[entry.task][index] = total_hours
            resource_data['Tot per Giorno'][1] += total_hours
            resource_data['Tot per Giorno'][index] += total_hours

        # Absences
        if entry.is_holiday:
            resource_data['Assenze'][index] = 'F'
            resource_data['Assenze'][1] += 8
        elif entry.is_sick_day:
            resource_data['Assenze'][index] = 'M'
            resource_data['Assenze'][1] += 8
        elif entry.leave_hours > 0 or entry.special_leave_hours > 0:
            _handles_leaves(entry, resource_data, index)

        # Other time entries
        for attr_name, label in timeentry_key_mapping.items():
            value = getattr(entry, attr_name)
            if value:
                resource_data[label][1] += value
                resource_data[label][index] += value


def _order_results(results: dict) -> dict:
    """Order the keys in the results dictionary for consistent output."""
    no_task_keys = [*list(timeentry_key_mapping.values()), 'Assenze', 'Tot per Giorno']
    ordered_results = {}
    for resource, data in results.items():
        task_items = {k: v for k, v in data.items() if k not in no_task_keys}
        no_task_items = {k: v for k, v in data.items() if k in no_task_keys}
        ordered_results[resource] = {**task_items, **no_task_items}
    return ordered_results


def _calculate_num_giorni_for_body(results: dict) -> None:
    """Calculate the 'num giorni' (day count) for the table body."""
    for body in results.values():
        for data in body.values():
            if isinstance(data, list) and data[1] is not None:
                data[0] = data[1] / 8


def timesheet_task_report_raw_data(
    from_date: datetime.date, to_date: datetime.date, resource: Resource | None = None
) -> dict['Resource', dict[str, list[D]]]:
    """
    Prepare the data for the timesheet report.

    If the resource is not provided, the report will be for all resources.
    """
    entry_qs = TimeEntry.objects.filter(date__gte=from_date, date__lte=to_date, resource__active=True).order_by(
        'resource', 'date'
    )
    task_qs = Task.objects.filter(start_date__lte=to_date).filter(Q(end_date__gte=from_date) | Q(end_date__isnull=True))

    if resource:
        entry_qs = entry_qs.filter(resource=resource)
        task_qs = task_qs.filter(resource=resource)

    days_interval = (to_date - from_date).days + 1

    results = _initialize_report_data(task_qs, days_interval)

    _calculate_work_days_for_resources(results, task_qs, from_date, to_date)

    start_date = KrmDay(from_date)
    _process_time_entries(results, entry_qs, start_date)

    results = _order_results(results)

    _calculate_num_giorni_for_body(results)

    return results


def task_report_data(current_month: str | None, user: User) -> dict[str, typing.Any]:
    """Prepare the data for the timesheet report."""
    if current_month is None:
        start_of_month = datetime.date.today().replace(day=1)
    else:
        start_of_month = datetime.datetime.strptime(current_month, '%Y%m').date()
    prev_month = start_of_month - relativedelta(months=1)
    next_month = start_of_month + relativedelta(months=1)

    end_of_month = start_of_month + relativedelta(months=1, days=-1)
    resource = None
    if not user.is_anonymous and not user.has_any_perm(
        'core.manage_any_timesheet', 'core.view_any_timesheet'
    ):
        resource = user.get_resource()
    data = timesheet_task_report_raw_data(start_of_month, end_of_month, resource=resource)

    for shifts in data.values():
        for key, values in shifts.items():
            if (isinstance(values, list)):
                shifts[key] = [format_data(v) if isinstance(v, D | int) else v for v in values]
    resources = Resource.objects.filter(active=True)
    if resource:
        resources = resources.filter(pk=resource.pk)
    data = dict.fromkeys(resources.order_by('last_name', 'first_name'), None) | data

    return {
        'prev_month': prev_month.strftime('%Y%m'),
        'current_month': start_of_month.strftime('%Y%m'),
        'next_month': next_month.strftime('%Y%m'),
        'title': start_of_month.strftime('%B %Y'),
        'days': list(KrmDay(start_of_month.strftime('%Y-%m-%d')).range_to(end_of_month)),
        'table_data': data,
    }
