import datetime
import json

from constance import config
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet

from krm3.config import settings
from krm3.core.models import Contract, Resource, TimeEntry
from krm3.timesheet.rules import Krm3Day
from krm3.utils.dates import KrmDay, get_country_holidays

User = get_user_model()


online_timeentry_key_mapping = {
    'bank': _('Bank hours'),
    'due_hours': _('Due hours'),
    'regular_hours': _('Regular hours'),
    'day_shift': _('Day shift hours'),
    'night_shift': _('Night shift hours'),
    'on_call': _('On call'),
    'travel': _('Travel'),
    'holiday': _('Holiday'),
    'leave': _('Leave'),
    'rest': _('Rest'),
    'overtime': _('Overtime'),
    'meal_voucher': _('Meal voucher'),
}


class TimesheetReport:
    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User, **kwargs) -> None:
        self._set_resources(user, **kwargs)
        resource_ids = {r.id for r in self.resources}

        self.from_date = from_date
        self.to_date = to_date

        self.default_schedule: dict[str, float] = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)

        top_period = to_date + datetime.timedelta(days=1) if to_date else None

        self.time_entries: list[TimeEntry] = list(self._get_time_entry_qs(resource_ids))

        self._load_submissions(from_date, top_period, resource_ids)

        self.country_codes: set[str] = {settings.HOLIDAYS_CALENDAR}
        self.resource_contracts: dict[int, list[Contract]] = {}

        for contract in list(
            Contract.objects.filter(period__overlap=(from_date, top_period), resource_id__in=resource_ids)
        ):
            self.resource_contracts.setdefault(contract.resource_id, []).append(contract)
            if contract.country_calendar_code and contract.country_calendar_code not in self.country_codes:
                self.country_codes.add(contract.country_calendar_code)

        self.extra_holidays = self._load_extra_holidays()
        self._holiday_cache = {}

        self.calendars: dict[int, list[Krm3Day]] = self._get_calendars()

    def _set_resources(self, user:User, **kwargs) -> None:
        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            self.resources = Resource.objects.filter(preferred_in_report=True)
        else:
            self.resources = [user.get_resource()]

    def _load_extra_holidays(self) -> dict[KrmDay, list[str]]:
        """Implement in children class if extra holidays need to be loaded."""
        return {}

    def _load_submissions(self, from_date: datetime.date, top_period: datetime.date, resource_ids: set[int]) -> (
            dict[int, list[tuple[datetime.date, datetime.date]]] | None):
        """Implement in children class if submissions need to be loaded."""
        return None

    def _get_holiday(self, kd: 'KrmDay', country_calendar_code: str) -> bool:
        """Return True if the day is holiday."""
        if res := self._holiday_cache.get((kd.date, country_calendar_code)):
            return res
        if (eh := self.extra_holidays.get(kd)) and (
            country_calendar_code in eh or country_calendar_code.split('-')[0] in eh
        ):
            hol = True
        else:
            cal = get_country_holidays(country_calendar_code=country_calendar_code)
            hol = not cal.is_working_day(kd.date)
        return self._holiday_cache.setdefault((kd.date, country_calendar_code), hol)

    def _get_calendars(self) -> dict[int, list[Krm3Day]]:
        """Return the dict of KrmDay in the interval for the resource id.

        The KrmDay is enriched with:
        - min_working_hours: the float min number of working hours expected by the resource in the day
        - is_holiday: is overridden with a bool
        """
        ret: dict[int, list[Krm3Day]] = {}
        for resource in self.resources:
            res_id = resource.id
            contracts: list[Contract] = self.resource_contracts.get(res_id) or []

            ret[res_id] = list(Krm3Day(self.from_date, resource=resource).range_to(self.to_date))

            for kd in ret[res_id]:
                kd.resource = resource
                for c in contracts:
                    if c.falls_in(kd):
                        kd.contract = c
                        break

                country_calendar_code = (
                    kd.contract.country_calendar_code
                    if kd.contract and kd.contract.country_calendar_code
                    else settings.HOLIDAYS_CALENDAR
                )
                kd.holiday = self._get_holiday(kd, country_calendar_code)
                min_working_hours = self._get_min_working_hours(kd)
                kd.nwd = kd.contract is None or kd.holiday or min_working_hours == 0
                if not kd.nwd:
                    kd.data_due_hours = min_working_hours
                submissions = getattr(self, 'submissions', {})
                for p_lower, p_upper in submissions.get(res_id, []):
                    if p_lower <= kd.date < p_upper:
                        kd.submitted = True
                kd.apply([te for te in self.time_entries if te.resource_id == res_id and te.date == kd.date])

        return ret

    def _get_min_working_hours(self, kd: Krm3Day) -> float:
        """Return the minimum working hours for a given KrmDay enriched with the eventual contract.

        NB: the function will not consider if it is holiday. The check must be performed by the caller.
        """
        if kd.contract and kd.contract.working_schedule:
            schedule = kd.contract.working_schedule
        else:
            schedule = self.default_schedule
        return schedule[kd.day_of_week_short.lower()]

    def _get_time_entry_qs(self, resource_ids: set[int]) -> QuerySet[TimeEntry]:
        """Return base time entry queryset with select related special_leave_reason."""
        return TimeEntry.objects.select_related('special_leave_reason').filter(
            date__gte=self.from_date, date__lte=self.to_date, resource_id__in=resource_ids
        )
