import datetime
import typing
from decimal import Decimal as D  # noqa: N817

from dateutil.relativedelta import relativedelta

from krm3.core.models import TimeEntry, Resource

from krm3.utils.dates import KrmDay


_fields = [
    'day_shift',
    'night_shift',
    'sick',
    'holiday',
    'leave',
    'on_call',
    'travel',
    'rest',
]


timeentry_key_mapping = {
    'day_shift': 'Ore ordinarie',
    'night_shift': 'Ore notturne',
    'on_call': 'Reperibilità',
    'travel': 'Viaggio',
    'holiday': 'Ferie',
    'leave': 'Permessi',
    'rest': 'Riposo',
    'sick': 'Malattia',
    'overtime': 'Ore straordinarie',
}


def timesheet_report_raw_data(
    from_date: datetime.date, to_date: datetime.date, resource: Resource | None = None
) -> dict['Resource', dict[str, list[D]]]:
    """
    Prepare the data for the timesheet report.

    If the resource is not provided, the report will be for all resources.

    Returns:
        A dictionary mapping resource names to a dict of time_entry_types with a list of
        Decimals summing up hours for each day.

    """
    qs = TimeEntry.objects.filter(date__gte=from_date, date__lte=to_date, resource__active=True).order_by(
        'resource', 'date'
    )

    if resource:
        qs = qs.filter(resource=resource)

    start_date = KrmDay(from_date)
    days_interval = (to_date - from_date).days + 1
    results = {}
    for entry in qs:
        date = KrmDay(entry.date)
        resource_stats = results.setdefault(entry.resource, {})

        index = date - start_date
        if entry.special_leave_reason:
            key = f'special_leave|{entry.special_leave_reason.id}'
            hours_types = resource_stats.setdefault(key, [D('0.00')] * days_interval)
            hours_types[index] += entry.special_leave_hours
        else:
            for field in _fields:
                hours_types = resource_stats.setdefault(field, [D('0.00')] * days_interval)
                hours_types[index] += getattr(entry, f'{field}_hours')

    for stats in results.values():
        stats['overtime'] = [D('0.00')] * days_interval

    return results


def add_report_summaries(results: dict) -> None:
    """Insert summary fields to the results at the beginning of each list."""
    for stats in results.values():
        for result_list in stats.values():
            result_list.insert(0, sum(result_list))
            for i in range(1, len(result_list)):
                if result_list[i] == D('0.00'):
                    result_list[i] = None


def calculate_overtime(resource_stats: dict) -> None:
    """Calculate overtime for each day."""
    for stats in resource_stats.values():
        num_days = len(stats['day_shift'])

        day_keys = [x for x in stats if x not in ['day_shift', 'night_shift', 'on_call', 'travel', 'rest', 'overtime']]

        for i in range(num_days):
            if sum([stats[x][i] for x in day_keys]) == D(0.0):
                tot_hours = stats['day_shift'][i] + stats['night_shift'][i] + stats['travel'][i]
                day_shift = min(D('8.00'), stats['day_shift'][i] + stats['night_shift'][i])
                stats['day_shift'][i] = day_shift
                stats['overtime'][i] = max(tot_hours - D('8.00'), D('0.00'))

def format_data(value: int) -> int | None | D:
    return value if value is None or value % 1 != 0 else int(value)


def timesheet_report_data(current_month: str | None) -> dict[str, typing.Any]:
    """Prepare the data for the timesheet report."""
    if current_month is None:
        start_of_month = datetime.date.today().replace(day=1)
    else:
        start_of_month = datetime.datetime.strptime(current_month, '%Y%m').date()
    prev_month = start_of_month - relativedelta(months=1)
    next_month = start_of_month + relativedelta(months=1)

    end_of_month = start_of_month + relativedelta(months=1, days=-1)
    data = timesheet_report_raw_data(start_of_month, end_of_month)
    calculate_overtime(data)
    add_report_summaries(data)

    for shifts in data.values():
        for key, values in shifts.items():
            shifts[key] = [format_data(v) for v in values]

    data = dict.fromkeys(Resource.objects.filter(active=True).order_by('last_name', 'first_name'), None) | data

    return {
        'prev_month': prev_month.strftime('%Y%m'),
        'current_month': start_of_month.strftime('%Y%m'),
        'next_month': next_month.strftime('%Y%m'),
        'title': start_of_month.strftime('%B %Y'),
        'days': list(KrmDay(start_of_month.strftime('%Y-%m-%d')).range_to(end_of_month)),
        'data': data,
        'keymap': timeentry_key_mapping,
    }
