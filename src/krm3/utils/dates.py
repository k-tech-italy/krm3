from __future__ import annotations

import datetime
import typing
from calendar import Calendar
from typing import Iterator, Self, override

import holidays
from dateutil.relativedelta import MO, SU, relativedelta
from django.utils.translation import gettext_lazy as _
from psycopg.types.range import DateRange, Range, T

from krm3.config.environ import env

if typing.TYPE_CHECKING:
    from krm3.types.krmdates import KrmDayType, MaybeKrmDayType, PeriodType


class KrmDay:
    max = datetime.date.max

    def __init__(self, day: MaybeKrmDayType = None, **kwargs) -> None:
        if day is None:
            day = datetime.date.today()
        if isinstance(day, KrmDay):
            self.date: datetime.date = day.date
        elif isinstance(day, datetime.date):
            self.date: datetime.date = day
        else:
            if len(day) == 10:
                self.date: datetime.date = datetime.datetime.strptime(day, '%Y-%m-%d').date()
            else:
                self.date: datetime.date = datetime.datetime.strptime(day, '%Y%m%d').date()
        self.__dict__.update(kwargs)

    @property
    def day(self) -> int:
        return self.date.day

    @property
    def month(self) -> int:
        return self.date.month

    @property
    def year(self) -> int:
        return self.date.year

    @property
    def day_of_year(self) -> int:
        return self.date.timetuple().tm_yday

    @property
    def week_of_year(self) -> int:
        return self.date.isocalendar()[1]

    def is_extra_holiday(self, country_calendar_code: str) -> bool:
        from krm3.core.models import ExtraHoliday  # noqa: PLC0415

        extra_holidays = ExtraHoliday.objects.filter(
            period__contains=self.date, country_codes__contains=[country_calendar_code]
        ).first()
        return bool(extra_holidays)

    def is_holiday(self, country_calendar_code: str = None, include_sundays_as_holiday: bool = True) -> bool:
        if country_calendar_code and self.is_extra_holiday(country_calendar_code):
            return True
        if include_sundays_as_holiday:
            return not get_country_holidays(country_calendar_code=country_calendar_code).is_working_day(self.date)
        return self.date in get_country_holidays(country_calendar_code=country_calendar_code)

    def is_non_working_day(self, country_calendar_code: str | None = None) -> bool:
        return self.day_of_week_short in ['Sat', 'Sun'] or self.is_holiday(country_calendar_code=country_calendar_code)

    @property
    def day_of_week(self) -> str:
        return self.date.strftime('%A')

    @property
    def day_of_week_short(self) -> str:
        return self.date.strftime('%a')

    @property
    def month_name(self) -> str:
        return self.date.strftime('%B')

    @property
    def month_name_short(self) -> str:
        return self.date.strftime('%b')

    def range_to(self, target: datetime.date | KrmDay) -> Iterator[Self]:
        """Iterate over all days between this day and the target day (including)."""
        if isinstance(target, datetime.date):
            target = self.__class__(target)
        if self.date > target.date:
            raise ValueError('Start date cannot be later than end date.')
        delta_days = (target.date - self.date).days
        for i in range(delta_days + 1):
            yield self + i

    def __eq__(self, __value: Self) -> bool:
        if not isinstance(__value, KrmDay):
            __value = KrmDay(__value)
        return self.date == __value.date

    def __hash__(self) -> int:
        return self.date.year * 10000 + self.date.month * 100 + self.date.day

    def __lt__(self, __value: Self) -> bool:
        if not isinstance(__value, KrmDay):
            __value = KrmDay(__value)
        return hash(self) < hash(__value)

    def __gt__(self, __value: Self) -> bool:
        if not isinstance(__value, KrmDay):
            __value = KrmDay(__value)
        return hash(self) > hash(__value)

    def __le__(self, __value: Self) -> bool:
        if not isinstance(__value, KrmDay):
            __value = KrmDay(__value)
        return hash(self) <= hash(__value)

    def __ge__(self, __value: Self) -> bool:
        if not isinstance(__value, KrmDay):
            __value = KrmDay(__value)
        return hash(self) >= hash(__value)

    def __sub__(self, other: Self | int | datetime.timedelta | relativedelta) -> int | KrmDay:
        """Subtract a number of days or a time period from this day."""
        if isinstance(other, KrmDay):
            return (self.date - other.date).days
        if isinstance(other, int):
            delta = relativedelta(days=other)
        elif isinstance(other, datetime.timedelta):
            delta = relativedelta(days=other.days)
        elif isinstance(other, relativedelta):
            delta = relativedelta(years=other.years, months=other.months, days=other.days)
        return KrmDay(self.date - delta)

    def __add__(self, other: int | datetime.timedelta | relativedelta) -> KrmDay:
        """Add a number of days or a time period to this day.

        If `other` is an `int`, it represents a number of days to add.

        If `other` is a `timedelta`, only days are taken into account,
        without any rounding.

        If `other` is a `relativedelta`, only years, months, days and
        weeks are taken into account. Any relative information with
        finer granularity than days and any absolute information is
        ignored.

        :param other: the number of days or period of time to add.
        :return: a new `KrmDay` instance.
        """
        if isinstance(other, int):
            delta = relativedelta(days=other)
        elif isinstance(other, datetime.timedelta):
            delta = relativedelta(days=other.days)
        elif isinstance(other, relativedelta):
            delta = relativedelta(years=other.years, months=other.months, days=other.days)
        return self.__class__(self.date + delta)

    def __repr__(self) -> str:
        return self.date.strftime('K%Y-%m-%d')

    def __str__(self) -> str:
        return self.date.strftime('%Y-%m-%d')


class KrmCalendar(Calendar):
    """A custom calendar class for KRM that generates KrmDays."""

    @override
    def __init__(self, firstweekday: int = 0) -> None:
        super().__init__(firstweekday)
        country, subdiv = str(env('HOLIDAYS_CALENDAR')).split('-')
        self.country_holidays = holidays.country_holidays(country, subdiv)

    @override
    def itermonthdates(self, year: int, month: int) -> Iterator[KrmDay]:
        return (KrmDay(x) for x in super().itermonthdates(year, month))

    @override
    def itermonthdays(self, year: int, month: int) -> Iterator[KrmDay | None]:
        for x in super().itermonthdays(year, month):
            yield KrmDay(datetime.date(year, month, x)) if x else None

    def iter_dates(self, from_date: KrmDayType, to_date: KrmDayType) -> Iterator[KrmDay]:
        """Iterate over all dates between from_date and to_date."""
        start = KrmDay(from_date)
        end = KrmDay(to_date)
        if start > end:
            raise ValueError('Start date cannot be after end date.')
        delta_days = (end.date - start.date).days

        for i in range(delta_days + 1):
            yield KrmDay(start.date + datetime.timedelta(days=i))

    def get_work_days(self, from_date: KrmDayType, to_date: KrmDayType) -> list[KrmDay]:
        days_between = self.iter_dates(from_date, to_date)

        return [day for day in days_between if not day.is_non_working_day()]

    def week_for(self, date: MaybeKrmDayType = None) -> tuple[KrmDay, KrmDay]:
        """Return the start and end date of the week for the given date.

        If no date is given, the current date is used.
        """
        date = KrmDay(date).date
        return KrmDay(date + relativedelta(weekday=MO(-1))), KrmDay(date + relativedelta(weekday=SU))

    def iter_week(self, date: datetime.date | str | None = None) -> Iterator[KrmDay]:
        """Iterate over all dates in the week for the given date.

        If no date is given, the current date is used.
        """
        return self.iter_dates(*self.week_for(date))


def get_country_holidays(country_calendar_code: str = None) -> holidays.HolidayBase:
    """Generate the appropriate country holidays."""
    hol_calendar = country_calendar_code or str(env('HOLIDAYS_CALENDAR'))
    subdiv = None
    if '-' in hol_calendar:
        country, subdiv = hol_calendar.split('-')
    else:
        country = hol_calendar
    cal = holidays.country_holidays(country, subdiv)
    cal.weekend = {6}  # SUN
    return cal


# Using 9999-09-09 allows to use +1 day unline datetime.date.max
DATE_INFINITE = datetime.date(9999, 9, 9)


class KrmDateRange(DateRange):
    """A specialised version of DateRange.

    It also accepts:
      - a DateRange
      - KrmDay | str as boundaries

    NB: Regardless of the bounds specified when saving the data, PostgreSQL always returns a range in a canonical form
        that includes the lower bound and excludes the upper bound, that is [)
        See https://docs.djangoproject.com/en/6.0/ref/contrib/postgres/fields/#daterangefield
    """

    def __init__(self, lower: T | None = None, upper: T | None = None, bounds: str = '[)', empty: bool = False) -> None:
        if isinstance(lower, Range):
            lower, upper, bounds, empty = lower.lower, lower.upper, lower.bounds, lower.isempty
        else:
            if isinstance(lower, (tuple, list)):
                lower, upper = lower
            lower, upper = KrmDay(lower).date if lower else None, KrmDay(upper).date if upper else None
        super().__init__(lower, upper, bounds, empty)
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(_('Lower bound must be smaller than upper bound'))

    @staticmethod
    def from_start_end(start_date: MaybeKrmDayType, end_date: MaybeKrmDayType):
        """Build a KrmDateRange from a start and end date (included)."""
        # upper = (KrmDay(end_date) + 1).date if end_date else None
        return KrmDateRange(lower=start_date, upper=end_date, bounds='[]')

    def fully_lt(self, other: PeriodType) -> bool:
        """Return True if the given date range is fully before than the other."""
        other = KrmDateRange(other).as_dates()
        return (self.upper or datetime.date.max) <= other.lower

    def fully_gt(self, other: PeriodType) -> bool:
        """Return True if the given date range is fully after than the other."""
        other = KrmDateRange(other).as_dates()
        return (self.lower or datetime.date.min) >= other.upper

    def startsbefore(self, other: PeriodType) -> bool:
        """Return True if the given date range start date is before the other's."""
        other = KrmDateRange(other).as_dates()
        return (self.lower or datetime.date.min) < other.lower

    def startsafter(self, other: PeriodType) -> bool:
        """Return True if the given date range start date is after the other's."""
        other = KrmDateRange(other).as_dates()
        return (self.lower or datetime.date.min) > other.lower

    def endsbefore(self, other: PeriodType) -> bool:
        """Return True if the given date range end date is before the other's."""
        other = KrmDateRange(other).as_dates()
        return (self.upper or datetime.date.max) < other.upper

    def endsafter(self, other: DateRange) -> bool:
        """Return True if the given date range end date is after the other's."""
        other = KrmDateRange(other).as_dates()
        return (self.upper or datetime.date.max) > other.upper

    def precedes(self, other: DateRange) -> bool:
        """Return True if the given date range is adjacent and precedes the other."""
        other = KrmDateRange(other).as_dates()
        return (self.upper or datetime.date.max) == other.lower

    def follows(self, other: DateRange) -> bool:
        """Return True if the given date range is adjacent and precedes the other."""
        other = KrmDateRange(other).as_dates()
        return (self.lower or datetime.date.min) == other.upper

    def as_dates(self) -> KrmDateRange:
        """Return the object as a PG DateRange replacing infinite boundaries with datetime.date.min/max."""
        return KrmDateRange(self.lower or datetime.date.min, self.upper or datetime.date.max, self.bounds, self.isempty)

    def contains(self, other: DateRange) -> bool:
        """Check if range contains other range."""
        other = KrmDateRange(other).as_dates()
        period = self.as_dates()
        return period.lower <= other.lower and period.upper >= other.upper

    def contained_by(self, other: DateRange) -> bool:
        """Check if range is contained by other range."""
        other = KrmDateRange(other).as_dates()
        period = self.as_dates()
        return period.lower >= other.lower and period.upper <= other.upper

    def overlap(self, other: DateRange) -> bool:
        """Check if range is overlapping other range."""
        other = KrmDateRange(other).as_dates()
        period = self.as_dates()
        return other.lower <= period.lower <= other.upper or period.lower <= other.upper <= period.upper

    def adjacent_to(self, other: DateRange) -> bool:
        """Check if range is adjacent to other range (touches at a boundary without overlapping)."""
        return self.precedes(other) or self.follows(other)

    @property
    def boundaries(self) -> tuple[datetime.date | None, datetime.date | None]:
        """Return the range's boundaries."""
        return self.lower, self.upper

    def __contains__(self, x: T) -> bool:
        """Accept dates and KrmDay compatible x."""
        return super().__contains__(KrmDay(x).date)

    def __iter__(self) -> Iterator[KrmDay]:
        """Return a KrmDay iterator over the days in the range.

        Return TypeError for unbounded ranges.
        """
        if self.lower in [None, datetime.date.min] or self.upper in [None, datetime.date.max]:
            raise TypeError(_('Cannot iterate over unbounded range'))
        dt = KrmDay(self.lower)
        for x in range((self.upper - self.lower).days):
            yield dt + x

    def __str__(self) -> str:
        res = f'[{self.lower:%Y-%m-%d}:' if self.lower not in [None, datetime.date.min] else '(...:'
        res += f'{self.upper:%Y-%m-%d})' if self.upper not in [None, datetime.date.max] else '...)'
        return res
