from __future__ import annotations

import datetime
from calendar import Calendar
from typing import Iterator, Self, override

import holidays
from dateutil.relativedelta import MO, SU, relativedelta

from krm3.config.environ import env


type _Date = KrmDay | datetime.date | str
type _MaybeDate = _Date | None


def dt(dat: str) -> datetime.date:
    """Parse a YYYY-MM-DD string."""
    return datetime.datetime.strptime(dat, '%Y-%m-%d').date()


class KrmDay:
    def __init__(self, day: _MaybeDate = None, **kwargs) -> None:
        if day is None:
            day = datetime.date.today()
        if isinstance(day, KrmDay):
            self.date = day.date
        elif isinstance(day, datetime.date):
            self.date = day
        else:
            self.date = dt(day)
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

    @property
    def is_holiday(self) -> bool:
        return not get_country_holidays().is_working_day(self.date)

    @property
    def is_non_working_day(self) -> bool:
        return self.day_of_week_short in ['Sat', 'Sun'] or self.is_holiday

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

    def range_to(self, target: datetime.date | KrmDay) -> Iterator[KrmDay]:
        """Iterate over all days between this day and the target day."""
        if isinstance(target, datetime.date):
            target = KrmDay(target)
        if self.date > target.date:
            raise ValueError('Start date cannot be later than end date.')
        delta_days = (target.date - self.date).days
        for i in range(delta_days + 1):
            yield self + i

    def __eq__(self, __value: Self) -> bool:
        return self.date == __value.date

    def __hash__(self) -> int:
        return self.date.year * 10000 + self.date.month * 100 + self.date.day

    def __gt__(self, __value: Self) -> bool:
        return hash(self) > hash(__value)

    def __ge__(self, __value: Self) -> bool:
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
        return KrmDay(self.date + delta)

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

    def iter_dates(self, from_date: _Date, to_date: _Date) -> Iterator[KrmDay]:
        """Iterate over all dates between from_date and to_date."""
        start = KrmDay(from_date)
        end = KrmDay(to_date)
        if start > end:
            raise ValueError('Start date cannot be after end date.')
        delta_days = (end.date - start.date).days

        for i in range(delta_days + 1):
            yield KrmDay(start.date + datetime.timedelta(days=i))

    def get_work_days(self, from_date: _Date, to_date: _Date) -> list[KrmDay]:

        days_between = self.iter_dates(from_date, to_date)

        return [day for day in days_between if not day.is_non_working_day]

    def week_for(self, date: _MaybeDate = None) -> tuple[KrmDay, KrmDay]:
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


def get_country_holidays() -> holidays.HolidayBase:
    """Generate the appropriate country holidays."""
    country, subdiv = str(env('HOLIDAYS_CALENDAR')).split('-')
    cal = holidays.country_holidays(country, subdiv)
    cal.weekend = {6}  # SUN
    return cal
