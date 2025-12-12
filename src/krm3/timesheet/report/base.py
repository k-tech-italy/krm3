from __future__ import annotations

from collections import defaultdict
import datetime
import json
from typing import TYPE_CHECKING

from constance import config
from django.utils.translation import gettext_lazy as _

from krm3.config import settings
from krm3.core.models import Contract, Resource, TimeEntry, TimesheetSubmission, ExtraHoliday
from krm3.timesheet.rules import Krm3Day
from krm3.utils.dates import KrmDay, get_country_holidays

if TYPE_CHECKING:
    from krm3.core.models import User as UserType


type _SubmissionPeriodData = dict[int, list[tuple[datetime.date, datetime.date]]]


def get_i18n_mapping() -> dict:
    return {
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
    # TODO: consider changing this into an `enum.Flag`, or use marker mixins/traits
    need: set = set()  # allowed values: 'submissions', 'extra_holidays'

    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: UserType, **kwargs) -> None:
        self.from_date = from_date
        self.to_date = to_date

        self.valid_contracts = Contract.objects.active_between(from_date, to_date)  # pyright: ignore
        self.resources = self._get_resources(user, **kwargs)

        self.default_schedule: dict[str, float] = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)

        self.time_entries = self._get_time_entries()

        # loading submissions up front, no matter the flags passed in
        # `need`, allows us to access all the pre-computed data in their
        # `timesheet` json field
        self.submissions = TimesheetSubmission.objects.get_closed_in_period(
            self.from_date, self.to_date, resources=self.resources
        )
        # TODO: get rid of this, only collect submissions
        self.submission_periods = self._get_submission_period_data()

        self.country_codes = {str(settings.HOLIDAYS_CALENDAR)}

        self.resource_contracts: dict[int, list[Contract]] = {}
        for contract in self.valid_contracts:
            self.resource_contracts.setdefault(contract.resource.pk, []).append(contract)
            if contract.country_calendar_code and contract.country_calendar_code not in self.country_codes:
                self.country_codes.add(contract.country_calendar_code)

        self.extra_holidays = self._get_extra_holidays() if 'extra_holidays' in self.need else {}
        self._holiday_cache = {}

        self.calendars = self._get_calendars()

    def _get_resources(self, user: UserType) -> list[Resource]:
        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            active_resource_ids = self.valid_contracts.values_list('resource', flat=True)
            return [*Resource.objects.filter(pk__in=active_resource_ids)]
        return [user.get_resource()]

    def _get_holiday(self, day: KrmDay, country_calendar_code: str) -> bool:
        """Return whether the day is holiday."""
        if res := self._holiday_cache.get((day.date, country_calendar_code)):
            return res
        if (eh := self.extra_holidays.get(day)) and (
            country_calendar_code in eh or country_calendar_code.split('-')[0] in eh
        ):
            hol = True
        else:
            cal = get_country_holidays(country_calendar_code=country_calendar_code)
            hol = not cal.is_working_day(day.date)
        return self._holiday_cache.setdefault((day.date, country_calendar_code), hol)

    def _get_calendars(self) -> dict[int, list[Krm3Day]]:
        """Return the dict of KrmDay in the interval for the resource id.

        The KrmDay is enriched with:
        - min_working_hours: the float min number of working hours expected by the resource in the day
        - is_holiday: is overridden with a bool
        """
        calendar_data: dict[int, list[Krm3Day]] = self._get_calendar_data_from_submissions()
        for resource in self.resources:
            resource_id = resource.pk
            contracts: list[Contract] = self.resource_contracts.get(resource_id) or []

            calendar_data[resource_id] = list(Krm3Day(self.from_date, resource=resource).range_to(self.to_date))

            for day in calendar_data[resource_id]:
                day.resource = resource
                for c in contracts:
                    if c.falls_in(day):
                        day.contract = c
                        break

                country_calendar_code = (
                    day.contract.country_calendar_code
                    if day.contract and day.contract.country_calendar_code
                    else str(settings.HOLIDAYS_CALENDAR)
                )
                day.holiday = self._get_holiday(day, country_calendar_code)
                min_working_hours = self._get_min_working_hours(day)
                day.nwd = day.contract is None or day.holiday or min_working_hours == 0
                if not day.nwd:
                    day.data_due_hours = min_working_hours
                for p_lower, p_upper in self.submission_periods.get(resource_id, []):
                    if p_lower <= day.date < p_upper:
                        day.submitted = True
                day.apply([te for te in self.time_entries if te.resource.pk == resource_id and te.date == day.date])

        return calendar_data

    def _get_min_working_hours(self, kd: Krm3Day) -> float:
        """Return the minimum working hours for a given day.

        This function only takes working hours into account, disregarding
        whether or not the day is a holiday or not. If you need to check
        for holiday, you should do it at the call site.
        """
        if kd.contract and kd.contract.working_schedule:
            schedule = kd.contract.working_schedule
        else:
            schedule = self.default_schedule
        return schedule[kd.day_of_week_short.lower()]

    def _get_time_entries(self) -> list[TimeEntry]:
        """Return a list of time entries, preloading their special leave reason if any."""
        return list(
            TimeEntry.objects.select_related('special_leave_reason').filter(
                date__gte=self.from_date, date__lte=self.to_date, resource__in=self.resources
            )
        )

    def _get_submission_period_data(self) -> _SubmissionPeriodData:
        submission_data = defaultdict(list)
        for ts in self.submissions:
            submission_data[ts.resource.pk].append((ts.period.lower, ts.period.upper))
        return submission_data

    def _get_extra_holidays(self) -> dict[KrmDay, list[str]]:
        """Retrieve the extra holidays for the given country codes."""
        short_codes = {x.split('-')[0] for x in self.country_codes}
        result = {}
        extra_holidays = list(
            ExtraHoliday.objects.filter(
                country_codes__overlap=list(self.country_codes.union(short_codes)),
                period__overlap=(self.from_date, self.to_date),
            )
        )
        for eh in extra_holidays:
            for kd in KrmDay(eh.period.lower).range_to(eh.period.upper - datetime.timedelta(days=1)):
                result.setdefault(kd, []).extend(eh.country_codes)
        return result

    def _get_calendar_data_from_submissions(self) -> dict[int, list[Krm3Day]]:
        calendar_data = defaultdict(list)

        for submission in self.submissions:
            calendar_data[submission.resource.pk].extend(Krm3Day.from_submission(submission))

        return calendar_data
