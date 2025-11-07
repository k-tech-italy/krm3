from collections.abc import Iterable
import datetime
import json

from constance import config
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from krm3.config import settings
from krm3.core.models import Contract, Resource, TimeEntry, TimesheetSubmission, ExtraHoliday
from krm3.timesheet.rules import Krm3Day
from krm3.utils.dates import KrmDay, get_country_holidays

User = get_user_model()

type _SubmissionData = dict[int, list[TimesheetSubmission]]
type _SubmissionPeriodData = dict[int, list[tuple[datetime.date, datetime.date]]]

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
    # TODO: consider changing this into an `enum.Flag`
    need: set = set()  # allowed values: 'submissions', 'extra_holidays'

    def __init__(self, from_date: datetime.date, to_date: datetime.date, user: User, **kwargs) -> None:
        self.resources = self._get_resources(user, **kwargs)

        self.default_schedule: dict[str, float] = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)

        self.from_date = from_date
        self.to_date = to_date

        self.time_entries = self._get_time_entries()

        # FIXME: `to_date` should disallow `None` to prevent unbounded date intervals
        top_period = to_date + datetime.timedelta(days=1) if to_date else None

        # loading submissions up front, no matter the flags passed in
        # `need`, allows us to access all the pre-computed data in their
        # `timesheet` json field
        self.submissions = TimesheetSubmission.objects.filter(
            resource__in=self.resources, closed=True, period__overlap=(from_date, top_period)
        )
        self.submission_periods = self._get_submissions(from_date, top_period)

        self.country_codes = {str(settings.HOLIDAYS_CALENDAR)}

        self.resource_contracts: dict[int, list[Contract]] = {}
        for contract in list(
            Contract.objects.filter(period__overlap=(from_date, top_period), resource__in=self.resources)
        ):
            self.resource_contracts.setdefault(contract.resource.pk, []).append(contract)
            if contract.country_calendar_code and contract.country_calendar_code not in self.country_codes:
                self.country_codes.add(contract.country_calendar_code)

        self.extra_holidays = self._get_extra_holidays() if 'extra_holidays' in self.need else {}
        self._holiday_cache = {}

        self.calendars = self._get_calendars()

    def _get_resources(self, user: User, **kwargs) -> Iterable[Resource]:
        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return Resource.objects.filter(preferred_in_report=True)
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

            for kd in calendar_data[resource_id]:
                kd.resource = resource
                for c in contracts:
                    if c.falls_in(kd):
                        kd.contract = c
                        break

                country_calendar_code = (
                    kd.contract.country_calendar_code
                    if kd.contract and kd.contract.country_calendar_code
                    else str(settings.HOLIDAYS_CALENDAR)
                )
                kd.holiday = self._get_holiday(kd, country_calendar_code)
                min_working_hours = self._get_min_working_hours(kd)
                kd.nwd = kd.contract is None or kd.holiday or min_working_hours == 0
                if not kd.nwd:
                    kd.data_due_hours = min_working_hours
                for p_lower, p_upper in self.submission_periods.get(resource_id, []):
                    if p_lower <= kd.date < p_upper:
                        kd.submitted = True
                kd.apply([te for te in self.time_entries if te.resource.pk == resource_id and te.date == kd.date])

        return calendar_data

    def _get_min_working_hours(self, kd: Krm3Day) -> float:
        """Return the minimum working hours for a given KrmDay enriched with the eventual contract.

        NB: the function will not consider if it is holiday. The check must be performed by the caller.
        """
        if kd.contract and kd.contract.working_schedule:
            schedule = kd.contract.working_schedule
        else:
            schedule = self.default_schedule
        return schedule[kd.day_of_week_short.lower()]

    def _get_time_entries(self) -> list[TimeEntry]:
        """Return base time entry queryset with select related special_leave_reason."""
        return list(
            TimeEntry.objects.select_related('special_leave_reason').filter(
                date__gte=self.from_date, date__lte=self.to_date, resource__in=self.resources
            )
        )

    # TODO: collect whole submissions, not just single fields
    def _get_submissions(self, from_date: datetime.date, top_period: datetime.date | None) -> _SubmissionPeriodData:
        submission_data = {}
        for ts in self.submissions:
            submission_data.setdefault(ts.resource.pk, []).append((ts.period.lower, ts.period.upper))
        return submission_data

    def _get_submission_timesheet(
        self, from_date: datetime.date, top_period: datetime.date | None
    ) -> _SubmissionPeriodData:
        submission_data = {}
        for ts in self.submissions:
            submission_data.setdefault(ts.resource.pk, []).append(ts.timesheet)
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
        return {}

        calendar_data = {}

        submission_data = {submission.resource.pk: submission for submission in self.submissions}
        for resource_id, submission in submission_data.items():
            timesheet = submission.timesheet
            # TODO: (WIP) generate `Krm3Day`s from the timesheets

        return calendar_data
