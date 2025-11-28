from collections.abc import Iterator
from dataclasses import dataclass
import datetime
from decimal import Decimal as D  # noqa: N817

import pytest
import tablib
from testutils.factories import SpecialLeaveReasonFactory

from krm3.timesheet.rules import TimesheetRule
from krm3.utils.dates import dt
from krm3.utils.numbers import safe_dec

# Mock TimeEntry model

out_fields = {
    'bank': 'bank',
    'day_shift': 'day_shift_hours',
    'regular_hours': 'regular_hours',
    'night_shift': 'night_shift_hours',
    'on_call': 'on_call_hours',
    'holiday': 'holiday_hours',
    'leave': 'leave_hours',
    'rest': 'rest_hours',
    'sick': 'sick_hours',
    'travel': 'travel_hours',
    'special_leave_reason': 'special_leave_reason',
    'special_leave_hours': 'special_leave_hours',
    'special_leave_reason_id': 'special_leave_reason_id',
    'overtime': 'overtime',
    'meal_voucher': 'meal_voucher',
    'fulfilled': 'fulfilled',
}


# FIXME: use factories
@dataclass(frozen=True)
class TimeEntryMock:
    date: datetime.date | str
    protocol_number: str | None
    bank_to: D | None
    bank_from: D | None
    day_shift_hours: D | None
    night_shift_hours: D | None
    on_call_hours: D | None
    travel_hours: D | None
    holiday_hours: D | None
    leave_hours: D | None
    rest_hours: D | None
    sick_hours: D | None
    special_leave_reason: str | None
    special_leave_hours: D | None

    # XXX: this is why we should use factories
    @property
    def special_hours(self):
        return (
            D(self.leave_hours or 0)
            + D(self.special_leave_hours or 0)
            + D(self.sick_hours or 0)
            + D(self.holiday_hours or 0)
        )

    @property
    def total_task_hours(self):
        return D(self.day_shift_hours or 0) + D(self.night_shift_hours or 0) + D(self.travel_hours or 0)


def column_index_to_name(n):
    """
    Converts a zero-based column index to a spreadsheet-style column name.
    (e.g., 0 -> 'A', 1 -> 'B', 26 -> 'AA').
    """
    name = ''
    while n >= 0:
        n, remainder = divmod(n, 26)
        name = chr(65 + remainder) + name
        n = n - 1
    return name


def _get_raw_scenarios(file_path: str) -> dict:
    with open(file_path, 'rb') as f:
        data = tablib.Dataset().load(f, 'ods')

    raw_scenarios = {}
    for row in data:
        if row and (header_name := row[0]):
            for col in range(1, len(row)):
                scen_name = column_index_to_name(col)
                d = raw_scenarios.setdefault(scen_name, {})
                d[header_name] = row[col]
    return raw_scenarios


def iterate_scenarios(raw_scenarios) -> Iterator[tuple]:
    for name, scenario in raw_scenarios.items():
        if scenario['special_leave_reason']:
            special_leave_reason = SpecialLeaveReasonFactory.build(title=scenario['special_leave_reason'])
        else:
            special_leave_reason = None
        time_entry = TimeEntryMock(
            date=dt('2020-04-13'),
            special_leave_reason=special_leave_reason,
            protocol_number=scenario['n. prot.'] if scenario['n. prot.'] else None,
            bank_from=safe_dec(scenario['bank_from (prelevo)'])
            if scenario['bank_from (prelevo)'] not in ('', None)
            else None,
            bank_to=safe_dec(scenario['bank_to (aggiungo)'])
            if scenario['bank_to (aggiungo)'] not in ('', None)
            else None,
            **{
                field: scenario[field]
                for field in [
                    'day_shift_hours',
                    'night_shift_hours',
                    'on_call_hours',
                    'travel_hours',
                    'holiday_hours',
                    'leave_hours',
                    'rest_hours',
                    'sick_hours',
                    'special_leave_hours',
                ]
            },
        )

        if val := scenario['special_leave_reason']:
            special_leave_title = val
        else:
            special_leave_title = None

        if bf := scenario['bank_from (prelevo)']:
            bank = -safe_dec(bf)
        elif bt := scenario['bank_to (aggiungo)']:
            bank = safe_dec(bt)
        else:
            bank = None

        expected = {
            'day_shift': safe_dec(scenario['day_shift_hours'])
            if scenario['day_shift_hours'] not in ('', None)
            else None,
            'night_shift': safe_dec(scenario['Ore Notturne']) if scenario['Ore Notturne'] not in ('', None) else None,
            'on_call': safe_dec(scenario['Reperibilità']) if scenario['Reperibilità'] not in ('', None) else None,
            'travel': safe_dec(scenario['travel_hours']) if scenario['travel_hours'] not in ('', None) else None,
            'holiday': safe_dec(scenario['Ferie']) if scenario['Ferie'] not in ('', None) else None,
            'leave': safe_dec(scenario['Permessi']) if scenario['Permessi'] not in ('', None) else None,
            'rest': safe_dec(scenario['Riposo']) if scenario['Riposo'] not in ('', None) else None,
            'sick': safe_dec(scenario['Malattie ']) if scenario['Malattie '] not in ('', None) else None,
            'special_leave_hours': scenario['Permessi Speciali ']
            if scenario['Permessi Speciali '] not in ('', None)
            else None,
            'special_leave_reason': special_leave_reason,
            'special_leave_title': special_leave_title,
            'protocol_number': scenario['n. prot.'] if scenario['n. prot.'] not in ('', None) else None,
            'regular_hours': safe_dec(scenario['Ore Ordinarie']) if scenario['Ore Ordinarie'] else None,
            'overtime': safe_dec(scenario['Ore Straordinarie']) if scenario['Ore Straordinarie'] else None,
            'meal_voucher': 1 if scenario['Buoni pasto'] == 1 else None,
            'bank': bank,
            'fulfilled': scenario['fulfilled'] == 'T',
        }

        due_hours = D(scenario['due_hours']) if scenario['due_hours'] not in ('', None) else None
        meal_threshold = D(scenario['meal_threshold']) if scenario['meal_threshold'] not in ('', None) else None

        yield name, due_hours, meal_threshold, time_entry, expected


def load_ods_data(file_path):
    """Loads test data from an ODS file."""
    raw_scenarios = _get_raw_scenarios(file_path)

    params = []
    for name, due_hours, meal_threshold, time_entry, expected in iterate_scenarios(raw_scenarios):
        params.append(pytest.param(due_hours, meal_threshold, [time_entry], expected, id=name))
    return params


@pytest.mark.django_db
@pytest.mark.parametrize(
    'due_hours, meal_threshold, time_entries, expected', load_ods_data('tests/examples/ReportPresenze (scenari).ods')
)
def test_calculate_from_ods(due_hours, meal_threshold, time_entries, expected, db):
    """
    Tests the TimesheetRule.calculate function using data from an ODS file.
    """
    # The 'description' parameter is not used in the test itself, but it's useful for debugging.
    # It's loaded from the ODS file and also used as the test ID.

    te = time_entries[0]
    if reason := te.special_leave_reason:
        reason.save()

    result = TimesheetRule.calculate(False, due_hours, meal_threshold, time_entries)

    assert result == expected
