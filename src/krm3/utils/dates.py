from calendar import Calendar
import datetime
from typing import Self, Iterator

import holidays
from dateutil.relativedelta import relativedelta, SU, MO

from krm3.config.environ import env


def dt(dat: str) -> datetime.date:
    """Just converts a YYYY-MM-DD string."""
    return datetime.datetime.strptime(dat, '%Y-%m-%d').date()


class KrmDay:

    def __init__(self, day: datetime.date | str = None) -> None:
        if day is None:
            day = datetime.date.today()
        if isinstance(day, KrmDay):
            self.date = day.date
        elif isinstance(day, datetime.date):
            self.date = day
        else:
            self.date = dt(day)

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
    def dd(self) -> int:
        return self.date.timetuple().tm_yday

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

    def reladd(self, days: int = None, **kwargs) -> Self:
        """Add a relativedelta to the KrmDay."""
        if days:
            kwargs['days'] = days
        return KrmDay(self.date + relativedelta(**kwargs))

    def range_to(self, target: datetime.date | Self) -> Iterator[Self]:
        """Iterate over all days between this day and the target day."""
        if isinstance(target, datetime.date):
            target = KrmDay(target)
        if self.date > target.date:
            raise ValueError("Start date cannot be after end date.")
        delta_days = (target.date - self.date).days
        for i in range(delta_days + 1):
            yield self + i

    def __eq__(self, __value: Self) -> bool:
        return self.date == __value

    def __hash__(self) -> int:
        return self.date.year * 10000 + self.date.month * 100 + self.date.day

    def __gt__(self, __value: Self) -> bool:
        return hash(self) > hash(__value)

    def __ge__(self, __value: Self) -> bool:
        return hash(self) >= hash(__value)

    def __sub__(self, __value: Self) -> int:
        return (self.date - __value.date).days

    def __add__(self, days: int) -> Self:
        return KrmDay(self.date + relativedelta(days=days))

    def __repr__(self) -> str:
        return self.date.strftime('K%Y-%m-%d')

    def __str__(self) -> str:
        return self.date.strftime('%Y-%m-%d')

class KrmCalendar(Calendar):
    """A custom calendar class for KRM that generates KrmDays."""

    def __init__(self, firstweekday: int=0) -> None:
        super().__init__(firstweekday)
        self.country_holidays = holidays.country_holidays(*env('HOLIDAYS_CALENDAR').split('-'))

    def itermonthdates(self, year: int, month: int) -> list[KrmDay]:
        return [KrmDay(x) for x in super().itermonthdates(year, month)]

    def itermonthdays(self, year: int, month: int) -> list[KrmDay]:
        return [KrmDay(datetime.date(year, month, x)) if x else None for x in super().itermonthdays(year, month)]

    def iter_dates(self, from_date: datetime.date | str, to_date: datetime.date | str) -> Iterator[KrmDay]:
        """Iterate over all dates between from_date and to_date."""
        from_date = KrmDay(from_date)
        to_date = KrmDay(to_date)
        if from_date > to_date:
            raise ValueError("Start date cannot be after end date.")
        delta_days = (to_date.date - from_date.date).days

        for i in range(delta_days + 1):
            yield KrmDay(from_date.date + datetime.timedelta(days=i))

    def week_for(self, dat: datetime.date | str = None) -> tuple[KrmDay, KrmDay]:
        """Return the start and end date of the week for the given date.

        If no date is given, the current date is used.
        """
        if not isinstance(dat, KrmDay):
            dat = KrmDay(dat)
        dat = dat.date
        return KrmDay(dat + relativedelta(weekday=MO(-1))), KrmDay(dat + relativedelta(weekday=SU))

    def iter_week(self, dat: datetime.date | str = None) -> Iterator[KrmDay]:
        """Iterate over all dates in the week for the given date.

        If no date is given, the current date is used.
        """
        return self.iter_dates(*self.week_for(dat))



def get_country_holidays() -> holidays.HolidayBase:
    """Generate the appropriate country holidays."""
    cal = holidays.country_holidays(*env('HOLIDAYS_CALENDAR').split('-'))
    cal.weekend ={6}  # SUN
    return cal
