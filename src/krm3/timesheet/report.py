import datetime
import typing
from decimal import Decimal

from krm3.core.models import TimeEntry
from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource


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


def timesheet_report_raw_data(
    from_date: datetime.date, to_date: datetime.date, resource: 'Resource' = None
) -> dict["Resource", dict[str, list[Decimal]]]:
    """
    Prepare the data for the timesheet report.

    If the resource is not provided, the report will be for all resources.

    Returns:
        A dictionary mapping resource names to a dict of time_entry_types with a list of
        Decimals summing up hours for each day.

    """
    qs = TimeEntry.objects.filter(date__gte=from_date, date__lte=to_date).order_by('resource', 'date')

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
            key = f'special_leave|{entry.special_leave_reason_id}'
            hours_types = resource_stats.setdefault(key, [Decimal('0.00')] * days_interval)
            hours_types[index] += entry.special_leave_hours
        else:
            for field in _fields:
                hours_types = resource_stats.setdefault(field, [Decimal('0.00')] * days_interval)
                # z = getattr(entry, f'{field}_hours')
                # if z > Decimal('0.0'):
                #     print(f'{field}: adding {z} to {hours_types[index]} from day {entry.date}')
                hours_types[index] += getattr(entry, f'{field}_hours')

    for resource, stats in results.items():
        stats['overtime'] = [Decimal('0.00')] * days_interval

    return results


def add_report_summaries(results):
    for resource, stats in results.items():
        for key, result_list in stats.items():
            result_list.insert(0, sum(result_list))
            for i in range(1, len(result_list)):
                if result_list[i] == Decimal('0.00'):
                    result_list[i] = None


def timesheet_report_sum():
    pass


def calculate_overtime(resource_stats):
    for resource, stats in resource_stats.items():
        num_days = len(stats['day_shift'])

        day_keys = [
            x for x in stats.keys() if x not in ['day_shift', 'night_shift', 'on_call', 'travel', 'rest', 'overtime']
        ]

        for i in range(num_days):
            if sum([stats[x][i] for x in day_keys]) == Decimal(0.0):
                day_shift = min(8, stats['day_shift'][i] + stats['night_shift'][i])
                extra_from_night_shift = max(stats['night_shift'][i] - (8 - stats[day_shift][i]), 0)

            hours_to_shift_from_night = min(8 - stats['day_shift'][i], stats['night_shift'][i])
            ord_hours = stats['day_shift'][i] + stats['night_shift'][i]

            # stats['overtime'][i] = stats['overtime'][i] / num_days
