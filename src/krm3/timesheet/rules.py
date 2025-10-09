import typing

from krm3.utils.dates import KrmDay, _MaybeDate
from krm3.utils.numbers import safe_dec

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract, TimeEntry

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
        self.data_special_leave = {}
        self.has_data = False
        self.nwd = False  # Non-working day
        self.submitted = False

    def __repr__(self) -> str:
        return self.date.strftime('K+%Y-%m-%d')

    def apply(self, time_entries: list['TimeEntry']) -> None:
        """Elaborates the krm3day data from the time_entries list."""
        self.time_entries = time_entries
        self.has_data = len(time_entries) > 0
        for k, v in TimesheetRule.calculate(not self.nwd, self.min_working_hours, time_entries).items():
            setattr(self, f'data_{k}', v)


class TimesheetRule:
    @staticmethod
    def calculate(work_day: bool, due_hours: float, time_entries: list['TimeEntry']) -> dict:  # noqa: C901,PLR0912
        """Calculate the time sheet rules for a set of time entries in a given work day.

        NB: time entries must be of same day.
        """
        if len({te.date for te in time_entries}) > 1:
            raise RuntimeError('Time entries must be of same day.')
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
            'special_leave_reason': None,
            'special_leave_hours': None,
            'protocol_number': None,
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
                'special_leave_hours',
                'special_leave_reason',
                'rest',
                'sick',
                'protocol_number',
            ]:
                te_key = (
                    key
                    if key in ['bank_to', 'bank_from', 'protocol_number', 'special_leave_hours', 'special_leave_reason']
                    else f'{key}_hours'
                )
                val = getattr(te, te_key)
                if key == 'protocol_number':
                    if val:
                        base['protocol_number'] = val
                elif val:
                    if key == 'special_leave_reason':
                        base['special_leave_reason'] = te.special_leave_reason.title
                    elif key == 'special_leave_hours':
                        base['special_leave_hours'] = safe_dec(val)
                    else:
                        base[key] = safe_dec(base[key]) + val

        if base['protocol_number'] and not base['sick']:
            base['protocol_number'] = None

        bank_to = base.pop('bank_to')
        bank_from = base.pop('bank_from')
        if bank_to or bank_from:
            base['bank'] = safe_dec(bank_to) - safe_dec(bank_from)
        else:
            base['bank'] = None

        special_activities = ['sick', 'holiday', 'leave']
        special_hours = sum(safe_dec(base[activity]) for activity in special_activities) + safe_dec(
            base['special_leave_hours']
        )
        if (
            special_hours == 0
            and (
                overtime := safe_dec(base['day_shift'])
                + safe_dec(base['night_shift'])
                + safe_dec(base['travel'])
                - safe_dec(base['bank'])
                - due_hours
            )
            > 0
        ):
            base['overtime'] = overtime
        return base
