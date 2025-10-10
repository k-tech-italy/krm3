from decimal import Decimal as D  # noqa: N817

import pytest
from testutils.date_utils import _dt
from testutils.factories import ResourceFactory, SpecialLeaveReasonFactory, TaskFactory

from krm3.core.models import TimeEntry
from krm3.timesheet.rules import TimesheetRule

base_te = {
    'day-entry': False,
    'bank': D(0),
    'day_shift': D(0),
    'night_shift': D(0),
    'on_call': D(0),
    'travel': D(0),
    'holiday': D(0),
    'leave': D(0),
    'rest': D(0),
    'sick': D(0),
    'special_leave_reason': None,
    'special_leave_hours': D(0),
}

base_results = {
    'bank': None,
    'day_shift': None,
    'night_shift': None,
    'on_call': None,
    'travel': None,
    'holiday': None,
    'leave': None,
    'rest': None,
    'sick': None,
    'special_leave_reason': None,
    'special_leave_hours': None,
    'overtime': None,
    'meal_voucher': None,
    'protocol_number': None,
}


@pytest.mark.parametrize(
    'work_day, due_hours, time_entries, expected',
    [
        pytest.param(True, 0, [], base_results, id='0due-empty-wd'),
        pytest.param(False, 0, [], base_results, id='0due-empty-nwd'),
        pytest.param(True, 8, [], base_results, id='8due-empty-wd'),
        pytest.param(False, 8, [], base_results, id='8due-empty-nwd'),
        pytest.param(
            True,
            8,
            [{'day_shift': 5, 'night_shift': 3}],
            base_results | {'day_shift': 5, 'night_shift': 3},
            id='8due-normal-wd',
        ),
        pytest.param(
            False,
            0,
            [{'day_shift': 5, 'night_shift': 3}],
            base_results | {'day_shift': 5, 'night_shift': 3, 'overtime': 8},
            id='0due-normal-nwd',
        ),
        pytest.param(
            True,
            8,
            [{'day_shift': 4, 'night_shift': 2}, {'night_shift': 3}],
            base_results | {'day_shift': 4, 'night_shift': 5, 'overtime': 1},
            id='8due-2tasks-wd-overtime',
        ),
        pytest.param(
            True,
            8,
            [{'sick': 8, 'day-entry': True}],
            base_results | {'sick': 8},
            id='8due-sick-wd',
        ),
        pytest.param(
            True,
            8,
            [{'sick': 8, 'protocol_number': '1234', 'day-entry': True}],
            base_results | {'sick': 8, 'protocol_number': '1234'},
            id='8due-8sick-with-protocol_number-wd',
        ),
        pytest.param(
            True,
            8,
            [{'holiday': 8, 'day-entry': True}],
            base_results | {'holiday': 8},
            id='8due-8holiday',
        ),
        pytest.param(
            False,
            0,
            [{'sick': 8, 'protocol_number': '101', 'day-entry': True}],
            base_results | {'sick': 8, 'protocol_number': '101'},
            id='8due-8sick-with-protocol_number-nwd',
        ),
        pytest.param(
            True,
            8,
            [{'leave': 4, 'day-entry': True}, {'day_shift': 4}],
            base_results | {'leave': 4, 'day_shift': 4},
            id='8due-4leave-wd',
        ),
        pytest.param(
            True,
            8,
            [{'rest': 4, 'day-entry': True}, {'day_shift': 4}],
            base_results | {'rest': 4, 'day_shift': 4},
            id='8due-4rest-wd',
        ),
        pytest.param(
            True,
            8,
            [{'on_call': 4}],
            base_results | {'on_call': 4},
            id='8due-4on_call-wd',
        ),
        pytest.param(
            True,
            8,
            [{'travel': 10}],
            base_results | {'travel': 10, 'overtime': 2},
            id='8due-10travel-with-overtime',
        ),
        pytest.param(
            True,
            8,
            [{'travel': 4}, {'day_shift': 4}, {'night_shift': 2}, {'on_call': 2}],
            base_results | {'travel': 4, 'day_shift': 4, 'night_shift': 2, 'on_call': 2, 'overtime': 2},
            id='8due-4travel-8-day-night_shift-2on_call-wd',
        ),
        pytest.param(
            True,
            8,
            [
                {'special_leave_reason': 'study', 'special_leave_hours': 6, 'day-entry': True},
                {'leave': 3, 'day-entry': True},
            ],
            base_results | {'leave': D(3), 'special_leave_reason': 'study', 'special_leave_hours': 6},
            id='8due-special_leave-with-leave-wd',
        ),
        pytest.param(
            True,
            8,
            [{'special_leave_reason': 'Law 104', 'special_leave_hours': 6, 'day-entry': True}],
            base_results | {'special_leave_reason': 'Law 104', 'special_leave_hours': 6},
            id='8due-special_leave-wd',
        ),
        pytest.param(
            True,
            8,
            [{'bank_from': 4, 'day-entry': True}, {'day_shift': 4}],
            base_results | {'bank': -4, 'day_shift': 4},
            id='8due-4bank_from-4-day_shift-wd',
        ),
        pytest.param(
            True,
            8,
            [{'day_shift': 10}, {'bank_to': 2, 'day-entry': True}],
            base_results | {'bank': 2, 'day_shift': 10},
            id='8due-10-day_shit-2bank_to-wd',
        ),
        pytest.param(
            True,
            8,
            [{'day_shift': 10}, {'bank_to': 1, 'day-entry': True}],
            base_results | {'bank': 1, 'day_shift': 10, 'overtime': 1},
            id='8due-1bank_to-10day_shift-wd',
        ),
        pytest.param(
            True,
            8,
            [{'day_shift': 2}, {'bank_from': 2, 'day-entry': True}, {'leave': 4, 'day-entry': True}],
            base_results | {'bank': -2, 'leave': 4, 'day_shift': 2},
            id='8due-4leave-2bank_from-2normal-wd',
        ),
        pytest.param(
            True,
            8,
            [{'day_shift': 4.5}, {'night_shift': 4.25}],
            base_results | {'day_shift': 4.5, 'night_shift': 4.25, 'overtime': 0.75},
            id='8due-fractional_hours',
        ),
        pytest.param(
            True,
            8,
            [{'sick': 4, 'day-entry': True}, {'day_shift': 5}],
            base_results | {'sick': 4, 'day_shift': 5},
            id='8due-4sick-5day_shift-without-overtime',
        ),
        pytest.param(
            True,
            8,
            [{'special_leave_reason': 'study', 'special_leave_hours': 2, 'day-entry': True}, {'day_shift': 5}],
            base_results | {'special_leave_reason': 'study', 'special_leave_hours': 2, 'day_shift': 5},
            id='8due-2special_leave-5-day_shift-wd',
        ),
    ],
)
def test_timesheet_rule_calculate(work_day, due_hours, time_entries, expected):
    resource = ResourceFactory()
    tes = []
    for time_entry in time_entries:
        te_kwargs = base_te | time_entry

        day_entry = te_kwargs.pop('day-entry')
        bank = te_kwargs.pop('bank', None)
        te_kwargs = {
            k
            if k in ['bank_from', 'bank_to', 'protocol_number', 'special_leave_hours', 'special_leave_reason']
            else f'{k}_hours': v
            for k, v in te_kwargs.items()
        }
        if reason := te_kwargs.pop('special_leave_reason'):
            te_kwargs['special_leave_reason'] = SpecialLeaveReasonFactory(title=reason)

        if not day_entry:
            te_kwargs['task'] = TaskFactory(resource=resource)
        if bank is not None:
            if bank > 0:
                time_entry['bank_to'] = bank
            else:
                time_entry['bank_from'] = bank
        tes.append(TimeEntry.objects.create(date=_dt('20251006'), resource=resource, **te_kwargs))
    assert TimesheetRule.calculate(work_day, due_hours, None, tes) == expected
