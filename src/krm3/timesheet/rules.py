from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from krm3.timesheet import utils
from krm3.utils import i18n
from ktcalendars import KTDay
from krm3.utils.numbers import safe_dec

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from krm3.core.models import Contract, DayEntry, Resource, TaskEntry, TimesheetSubmission
    from ktcalendars.types import KTDayType

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


class Krm3Day(KTDay):
    def __init__(self, day: KTDayType = None, **kwargs) -> None:
        self.lang: str = 'IT'
        super().__init__(day, **kwargs)
        self.resource: 'Resource | None' = None
        self.data_due_hours = Decimal.from_float(0)
        self.contract: 'Contract | None' = None
        self.holiday: bool = False
        self.time_entries: Iterable[TaskEntry] = []
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
        self.data_meal_voucher_threshold = None
        self.data_special_leave_hours = None
        self.data_special_leave_reason = None
        self.data_regular_hours = None
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

    def apply(self, day_entry: DayEntry | None, task_entries: list[TaskEntry]) -> None:
        """Populate report data from the day-level and task-level entries."""
        self.time_entries = task_entries
        self.has_data = day_entry is not None or bool(task_entries)
        if day_entry is None:
            return

        def value_or_none(value: Decimal | int) -> Decimal | int | None:
            return value if value else None

        due_hours = safe_dec(day_entry.due_hours) or safe_dec(self.data_due_hours)
        worked_hours = sum((safe_dec(entry.total_task_hours) for entry in task_entries), start=Decimal(0))
        bank = safe_dec(day_entry.bank)

        self.data_due_hours = due_hours
        self.data_bank = value_or_none(bank)
        self.data_bank_to = value_or_none(max(bank, Decimal(0)))
        self.data_bank_from = value_or_none(max(-bank, Decimal(0)))
        self.data_day_shift = value_or_none(
            sum((safe_dec(entry.day_shift_hours) for entry in task_entries), start=Decimal(0))
        )
        self.data_night_shift = value_or_none(
            sum((safe_dec(entry.night_shift_hours) for entry in task_entries), start=Decimal(0))
        )
        self.data_on_call = value_or_none(
            sum((safe_dec(entry.on_call_hours) for entry in task_entries), start=Decimal(0))
        )
        self.data_travel = value_or_none(
            sum((safe_dec(entry.travel_hours) for entry in task_entries), start=Decimal(0))
        )
        self.data_holiday = due_hours if day_entry.asked_holiday else None
        self.data_leave = value_or_none(day_entry.leave_hours)
        self.data_special_leave_hours = value_or_none(day_entry.special_leave_hours)
        self.data_special_leave_reason = day_entry.special_leave_reason
        self.data_protocol_number = day_entry.protocol_number
        self.data_rest = value_or_none(day_entry.rest_hours)
        self.data_sick = due_hours if day_entry.is_sick else None
        self.data_overtime = value_or_none(day_entry.overtime_hours)
        self.data_meal_voucher = value_or_none(day_entry.meal_voucher)
        regular_hours = min(max(worked_hours - bank, Decimal(0)), due_hours)
        self.data_regular_hours = value_or_none(regular_hours)

    @classmethod
    def from_submission(cls, submission: TimesheetSubmission) -> Iterator:
        """Convert the timesheet data from a `TimesheetSubmission`.

        :param submission: the `TimesheetSubmission` to convert
        :return: a lazy sequence of `Krm3Day`s covering the submission's time period
        """
        from krm3.core.models import Contract, DayEntry, SpecialLeaveReason, TaskEntry

        timesheet_data = submission.timesheet or {}
        if 'day_entries' not in timesheet_data:
            yield from cls._from_legacy_submission(submission)
            return

        serialized_day_entries = timesheet_data.get('day_entries', [])
        serialized_task_entries = timesheet_data.get('task_entries', [])
        serialized_days = timesheet_data.get('days', [])
        schedule = timesheet_data.get('schedule', {})

        contracts = list(
            Contract.objects.filter(resource=submission.resource, period__overlap=submission.period).order_by('period')
        )
        contracts_by_id = {contract.pk: contract for contract in contracts}
        special_leave_reason_ids = {
            entry_data['special_leave_reason']
            for entry_data in serialized_day_entries
            if entry_data.get('special_leave_reason') is not None
        }
        special_leave_reasons = SpecialLeaveReason.objects.in_bulk(special_leave_reason_ids)

        def decimal_value(value: str | int | float | Decimal | None) -> Decimal:
            return Decimal(str(value or 0))

        day_entries_by_id: dict[int, DayEntry] = {}
        day_entries_by_date: dict[datetime.date, DayEntry] = {}
        for entry_data in serialized_day_entries:
            entry_date = datetime.date.fromisoformat(entry_data['day'])
            day_entry = DayEntry(
                id=entry_data['id'],
                day=entry_date,
                resource=submission.resource,
                contract=contracts_by_id[entry_data['contract']],
                bank=decimal_value(entry_data.get('bank')),
                due_hours=decimal_value(entry_data.get('due_hours')),
                travel_hours=decimal_value(entry_data.get('travel_hours')),
                day_hours=decimal_value(entry_data.get('day_hours')),
                night_hours=decimal_value(entry_data.get('night_hours')),
                on_call_hours=decimal_value(entry_data.get('on_call_hours')),
                is_holiday=bool(entry_data.get('is_holiday')),
                asked_holiday=bool(entry_data.get('asked_holiday')),
                leave_hours=decimal_value(entry_data.get('leave_hours')),
                special_leave_hours=decimal_value(entry_data.get('special_leave_hours')),
                special_leave_reason=special_leave_reasons.get(entry_data.get('special_leave_reason')),
                protocol_number=entry_data.get('protocol_number'),
                is_sick=bool(entry_data.get('is_sick')),
                rest_hours=decimal_value(entry_data.get('rest_hours')),
                overtime_hours=decimal_value(entry_data.get('overtime_hours')),
                meal_voucher=int(entry_data.get('meal_voucher') or 0),
            )
            day_entries_by_id[entry_data['id']] = day_entry
            day_entries_by_date[entry_date] = day_entry

        task_entries_by_day_entry_id: dict[int, list[TaskEntry]] = {}
        for entry_data in serialized_task_entries:
            day_entry_id = entry_data['day_entry']
            day_entry = day_entries_by_id.get(day_entry_id)
            if day_entry is None:
                continue
            task_entry = TaskEntry(
                id=entry_data['id'],
                day_entry=day_entry,
                task_id=entry_data['task'],
                day_shift_hours=decimal_value(entry_data.get('day_shift_hours')),
                night_shift_hours=decimal_value(entry_data.get('night_shift_hours')),
                on_call_hours=decimal_value(entry_data.get('on_call_hours')),
                travel_hours=decimal_value(entry_data.get('travel_hours')),
                comment=entry_data.get('comment'),
                metadata=entry_data.get('metadata'),
            )
            task_entries_by_day_entry_id.setdefault(day_entry_id, []).append(task_entry)

        for serialized_day in serialized_days:
            day_date = datetime.date.fromisoformat(serialized_day)
            day_entry = day_entries_by_date.get(day_date)
            contract = day_entry.contract if day_entry is not None else next(
                (candidate for candidate in contracts if day_date in candidate.period), None
            )
            contract_day = contract.get_ktday(day_date, silent=True) if contract is not None else None

            day = cls(day=day_date)
            day.submitted = True
            day.resource = submission.resource
            day.contract = contract
            day.holiday = day_entry.is_holiday if day_entry is not None else bool(contract_day and contract_day.is_holiday)
            day.data_due_hours = (
                day_entry.due_hours if day_entry is not None else decimal_value(schedule.get(serialized_day))
            )
            day.nwd = contract is None or day.holiday or day.data_due_hours == 0
            task_entries = task_entries_by_day_entry_id.get(day_entry.pk, []) if day_entry is not None else []
            day.apply(day_entry, task_entries)
            yield day

    @classmethod
    def _from_legacy_submission(cls, submission: TimesheetSubmission) -> Iterator:
        """Convert a submission saved before DayEntry and TaskEntry were introduced."""
        from krm3.core.models import Contract, SpecialLeaveReason

        timesheet_data = submission.timesheet or {}
        serialized_days = timesheet_data.get('days', {})
        serialized_entries = timesheet_data.get('time_entries', [])
        schedule = timesheet_data.get('schedule', {})

        contracts = list(
            Contract.objects.filter(resource=submission.resource, period__overlap=submission.period).order_by('period')
        )
        special_leave_reason_ids = {
            entry_data['special_leave_reason']
            for entry_data in serialized_entries
            if entry_data.get('special_leave_reason') is not None
        }
        special_leave_reasons = SpecialLeaveReason.objects.in_bulk(special_leave_reason_ids)

        def decimal_value(value: str | int | float | Decimal | None) -> Decimal:
            return Decimal(str(value or 0))

        entries_by_date: dict[str, list[dict]] = {}
        for entry_data in serialized_entries:
            entries_by_date.setdefault(entry_data['date'], []).append(entry_data)

        for serialized_day, day_data in serialized_days.items():
            day_date = datetime.date.fromisoformat(serialized_day)
            contract = next((candidate for candidate in contracts if day_date in candidate.period), None)
            day_entries = entries_by_date.get(serialized_day, [])

            def total(field: str) -> Decimal:
                return sum((decimal_value(entry.get(field)) for entry in day_entries), start=Decimal(0))

            bank_to = total('bank_to')
            bank_from = total('bank_from')
            bank = bank_to - bank_from
            due_hours = decimal_value(schedule.get(serialized_day))
            task_hours = total('day_shift_hours') + total('night_shift_hours') + total('travel_hours')
            worked_hours = task_hours + max(bank_from - bank_to, Decimal(0))
            special_leave_reason_id = next(
                (entry.get('special_leave_reason') for entry in day_entries if entry.get('special_leave_reason')), None
            )

            day = cls(day=day_date)
            day.submitted = True
            day.resource = submission.resource
            day.contract = contract
            day.holiday = bool(day_data.get('hol'))
            day.nwd = bool(day_data.get('nwd'))
            day.data_due_hours = due_hours
            day.data_bank = bank or None
            day.data_bank_to = bank_to or None
            day.data_bank_from = bank_from or None
            day.data_day_shift = total('day_shift_hours') or None
            day.data_night_shift = total('night_shift_hours') or None
            day.data_on_call = total('on_call_hours') or None
            day.data_travel = total('travel_hours') or None
            day.data_holiday = total('holiday_hours') or None
            day.data_leave = total('leave_hours') or None
            day.data_special_leave_hours = total('special_leave_hours') or None
            day.data_special_leave_reason = special_leave_reasons.get(special_leave_reason_id)
            day.data_protocol_number = next(
                (entry.get('protocol_number') for entry in day_entries if entry.get('protocol_number')), None
            )
            day.data_rest = total('rest_hours') or None
            day.data_sick = total('sick_hours') or None
            day.data_overtime = decimal_value(day_data.get('overtime')) or None
            day.data_meal_voucher = decimal_value(day_data.get('meal_voucher')) or None
            regular_hours = min(worked_hours, due_hours)
            day.data_regular_hours = regular_hours or None
            day.has_data = bool(day_entries)
            yield day


class TimesheetRule:
    @staticmethod
    def calculate(  # noqa: C901,PLR0912
        work_day: bool, due_hours: float, meal_voucher_threshold: float | None, time_entries: 'Iterable[TimeEntry]'
    ) -> dict:
        """Calculate the time sheet rules for a set of time entries in a given work day.

        NB: time entries must be of same day.
        """
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
