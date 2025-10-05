from decimal import Decimal as D
import typing

from krm3.utils.dates import KrmDay, _MaybeDate

if typing.TYPE_CHECKING:
    from krm3.core.models import TimeEntry, Contract

timeentry_counters = {
    'bank': 'Banca ore',
    'day_shift': 'Ore ordinarie',
    'night_shift': 'Ore notturne',
    'on_call': 'Reperibilità',
    'travel': 'Viaggio',
    'holiday': 'Ferie',
    'leave': 'Permessi',
    'rest': 'Riposo',
    'sick': 'Malattia',
    'overtime': 'Ore straordinarie',
    'meal_voucher': 'Buoni pasto',
}


def SD(val: int | float | str | D | None) -> D:
    """Return the val in Decimal format or Decimal(0) is value is None."""
    if val is None:
        return D(0)
    elif isinstance(val, D):
        return val
    else:
        return D(val)

class Krm3Day(KrmDay):
    def __init__(self, day: _MaybeDate = None, **kwargs) -> None:
        super().__init__(day, **kwargs)
        self.resource = None
        self.min_working_hours: float = 0
        self.contract: Contract | None = None
        self.holiday: bool = False
        self.time_entries: list[TimeEntry] = []
        self.data_bank = None
        self.data_day_shift = None
        self.data_night_shift = None
        self.data_on_call = None
        self.data_travel = None
        self.data_holiday = None
        self.data_leave = None
        self.data_rest = None
        self.data_sick = None
        self.data_overtime = None
        self.data_meal_voucher = None
        self.data_special_leaves = {}
        self.has_data = False
        self.nwd = False  # Non-working day
        self.submitted = False

    def __repr__(self) -> str:
        return self.date.strftime('K+%Y-%m-%d')

    def apply(self, time_entries: list['TimeEntry']):
        """Elaborates the krm3day data from the time_entries list."""
        self.time_entries = time_entries
        self.has_data = len(time_entries) > 0
        for k, v in TimesheetRule.calculate(not self.nwd, self.min_working_hours, time_entries).items():
            setattr(self, f'data_{k}', v)


class TimesheetRule:
    @staticmethod
    def calculate(work_day: bool, due_hours: float, time_entries: list['TimeEntry']) -> dict:
        base = {
            'bank_to': None,
            'bank_from': None,
            'day_shift': None,
            'night_shift': None,
            'on_call': None,
            'travel': None,
            'holiday': None,
            'leave': None,
            'rest': None,
            'sick': None,
            'overtime': None,
            'meal_voucher': None,
            'special_leave': {},
        }
        for te in time_entries:
            for key in [
                'bank_to',
                'bank_from',
                'day_shift',
                'night_shift',
                'on_call',
                'travel',
                'holiday',
                'leave',
                'special_leave',
                'rest',
                'sick',
            ]:
                te_key = key if key in ['bank_to', 'bank_from'] else f'{key}_hours'
                if val := getattr(te, te_key):
                    if key == 'special_leave':
                        base['special_leave'][te.special_leave_reason_id] = SD(base['special_leave'].get(te.special_leave_reason_id)) + SD(val)
                    else:
                        base[key] = SD(base[key]) + val

        bank_to = base.pop('bank_to')
        bank_from = base.pop('bank_from')
        if bank_to or bank_from:
            base['bank'] = SD(bank_to) - SD(bank_from)
        else:
            base['bank'] = None
        special_activities = ['sick', 'holiday', 'leave']
        special_hours = sum(SD(base[activity]) for activity in special_activities)
        if base['special_leave']:
            # Only 1 special leave allowed as per business rule
            special_hours += SD(list(base['special_leave'].values())[0])
        if special_hours == 0:
            if (overtime := SD(base['day_shift']) + SD(base['night_shift']) - SD(base['bank']) - due_hours) > 0:
                base['overtime'] = overtime
        return base
        # return {k: random.randint(0, 8) if work_day else '' for k in timeentry_counters.keys() }
