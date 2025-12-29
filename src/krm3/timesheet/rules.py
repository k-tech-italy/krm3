from __future__ import annotations

from decimal import Decimal
from typing import Any, TYPE_CHECKING

from krm3.core.models import Contract, TimeEntry, Resource
from krm3.timesheet import utils
from krm3.utils import i18n
from krm3.utils.dates import KrmDay, _MaybeDate
from krm3.utils.numbers import safe_dec

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from krm3.core.models import TimesheetSubmission

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

te_calc_map = {
    'bank_to': 'bank_to',
    'bank_from': 'bank_from',
    'day_shift_hours': 'day_shift',
    'night_shift_hours': 'night_shift',
    'on_call_hours': 'on_call',
    'travel_hours': 'travel',
    'holiday_hours': 'holiday',
    'leave_hours': 'leave',
    'special_leave_reason': 'special_leave_reason',
    'special_leave_hours': 'special_leave_hours',
    'protocol_number': 'protocol_number',
    'rest_hours': 'rest',
    'sick_hours': 'sick',
}


class Krm3Day(KrmDay):
    def __init__(self, day: _MaybeDate = None, **kwargs) -> None:
        self.lang: str = 'IT'
        super().__init__(day, **kwargs)
        self.resource: Resource | None = None
        self.data_due_hours = Decimal.from_float(0)
        self.contract: Contract | None = None
        self.holiday: bool = False
        self.time_entries: Iterable[TimeEntry] = []
        self.data_bank = None
        self.data_bank_from = None
        self.data_bank_to = None
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
        self.data_special_leave_hours = None
        self.data_special_leave_reason = None
        self.has_data: bool = False

        self.nwd: bool = False
        """`True` if this is a non-working day, `False` otherwise."""

        self.submitted = False
        self.data_protocol_number: str | None = None

    def __repr__(self) -> str:
        return self.date.strftime('K+%Y-%m-%d')

    @property
    def day_of_week_short_i18n(self) -> str:
        return i18n.short_day_of_week(self.date)

    def apply(self, time_entries: list[TimeEntry]) -> None:
        """Compute the krm3day data from the time_entries list."""
        self.time_entries = time_entries
        self.has_data = bool(time_entries)
        meal_voucher_threshold = None
        if self.contract and (thresholds := self.contract.meal_voucher):
            meal_voucher_threshold = thresholds.get('sun' if self.nwd else self.day_of_week_short.lower())
        for k, v in TimesheetRule.calculate(
                not self.nwd, float(self.data_due_hours), meal_voucher_threshold, time_entries
        ).items():
            setattr(self, f'data_{k}', v)

    @classmethod
    def from_submission(cls, submission: TimesheetSubmission) -> Iterator:
        """Convert the timesheet data from a `TimesheetSubmission`.

        :param submission: the `TimesheetSubmission` to convert
        :return: a lazy sequence of `Krm3Day`s covering the submission's time period
        """
        timesheet_data = submission.timesheet or {}

        # NOTE: there is no point in computing totals from serialized
        #       data if we have to populate the objects with model
        #       instances anyway - just get the instances up front.
        #       DRF serializers are also out of the question due to
        #       only allowing to deserialize model instances via
        #       `create()` or `update()`.
        time_entries = TimeEntry.objects.filter(
            id__in=(entry_data['id'] for entry_data in timesheet_data.get('time_entries', []))
        )
        contracts = Contract.objects.filter(
            id__in=(contract_data['id'] for contract_data in timesheet_data.get('contracts', []))
        )

        def _extract(key: str, from_: Iterable[dict]) -> Iterator:
            return (entry[key] for entry in from_)

        for date, day_data in timesheet_data.get('days', {}).items():
            day = Krm3Day(day=date)

            this_day_time_entries = time_entries.filter(date=date)
            this_day_time_entry_data = [
                entry_data for entry_data in timesheet_data.get('time_entries', []) if entry_data['date'] == date
            ]

            try:
                contract = contracts.filter(period__contains=date).get()
            except Contract.DoesNotExist:
                contract = None

            day.resource = submission.resource
            day.contract = contract
            day.holiday = day_data.get('hol')
            day.nwd = day_data.get('nwd')
            day.time_entries = this_day_time_entries
            day.data_bank = Decimal(timesheet_data.get('bank_hours', 0))
            day.data_day_shift = sum(map(Decimal, _extract('day_shift_hours', this_day_time_entry_data)))
            day.data_night_shift = sum(map(Decimal, _extract('night_shift_hours', this_day_time_entry_data)))
            day.data_on_call = sum(map(Decimal, _extract('on_call_hours', this_day_time_entry_data)))
            day.data_travel = sum(map(Decimal, _extract('travel_hours', this_day_time_entry_data)))
            day.data_holiday = sum(map(Decimal, _extract('holiday_hours', this_day_time_entry_data)))
            day.data_leave = sum(map(Decimal, _extract('leave_hours', this_day_time_entry_data)))
            day.data_special_leave_hours = sum(map(Decimal, _extract('special_leave_hours', this_day_time_entry_data)))
            day.data_special_leave_reason = (
                    ', '.join(reason for entry_data in this_day_time_entry_data if
                              (reason := entry_data['special_leave_reason']))
                    or None
            )
            day.data_rest = sum(map(Decimal, _extract('rest_hours', this_day_time_entry_data)))
            day.data_sick = sum(map(Decimal, _extract('sick_hours', this_day_time_entry_data)))
            day.data_bank_from = sum(map(Decimal, _extract('bank_from', this_day_time_entry_data)))
            day.data_bank_to = sum(map(Decimal, _extract('bank_to', this_day_time_entry_data)))
            day.data_due_hours = (
                contract.get_due_hours(day.date) if contract else Contract.get_default_schedule(day.date)
            )
            day.data_meal_voucher = day_data.get('meal_voucher')
            # XXX: a property would be nicer, as this piece of information depends on other attributes
            day.has_data = this_day_time_entries.exists()

            yield day


class TimesheetRule:
    @staticmethod
    def calculate(  # noqa: C901,PLR0912
            work_day: bool, due_hours: float, meal_voucher_threshold: float | None, time_entries: list['TimeEntry']
    ) -> dict:
        """Calculate the time sheet rules for a set of time entries in a given work day.

        NB: time entries must be of same day.
        """
        utils.verify_time_entries_from_same_day(time_entries)
        base: dict[str, Any] = {
            'bank_to': None,
            'bank_from': None,
            'day_shift': None,
            'night_shift': None,
            'on_call': None,
            'holiday': None,
            'travel': None,
            'leave': None,
            'rest': None,
            'sick': None,
            'overtime': None,
            'meal_voucher': None,
            'special_leave_reason': None,
            'special_leave_title': None,
            'special_leave_hours': None,
            'protocol_number': None,
        }
        for te in time_entries:
            for fname, key in te_calc_map.items():
                if val := getattr(te, fname):
                    if fname in ['protocol_number', 'special_leave_reason']:
                        base[key] = val
                    else:
                        base[key] = safe_dec(base[key]) + safe_dec(val)
            if val := base['special_leave_reason']:
                base['special_leave_title'] = val.title
        bank_to = base.pop('bank_to')
        bank_from = base.pop('bank_from')
        if bank_to or bank_from:
            base['bank'] = safe_dec(bank_to) - safe_dec(bank_from)
        else:
            base['bank'] = None

        # here it doesn't matter whether overtime applies or not
        # if there's no overtime, don't show anything regardless
        overtime = utils.overtime(time_entries, safe_dec(due_hours))
        base['overtime'] = overtime if overtime != 0 else None

        worked_hours = safe_dec(utils.worked_hours(time_entries))
        special_hours = safe_dec(utils.special_hours(time_entries))
        if meal_voucher_threshold and meal_voucher_threshold <= worked_hours:
            base['meal_voucher'] = 1

        regular_hours = safe_dec(utils.regular_hours(time_entries, safe_dec(due_hours)))
        fulfilled_hours = worked_hours + special_hours + safe_dec(base['rest'])
        base['fulfilled'] = fulfilled_hours >= safe_dec(due_hours)

        base['regular_hours'] = regular_hours if regular_hours != Decimal(0) else None
        return base
