# https://pypi.org/project/holidays/
import enum

import calendar
import datetime
import threading
import typing
from collections import OrderedDict
from functools import lru_cache

import holidays
from django.conf import settings

from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract

CACHE_SIZE = 30

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


class DayKind(enum.Enum):
    HOLIDAY = 'holiday'  # bank/public holiday, or the weekly rest day
    WEEKEND = 'weekend'  # non-working, but not a holiday
    WORKING_DAY = 'working day'


@lru_cache(maxsize=64)
def get_calendar(country_code: str, subdiv: str | None = None) -> holidays.HolidayBase:
    """Build (and cache) the holiday calendar. Accepts 'IT' or ISO 3166-2 'IT-RM'."""
    if subdiv is None and '-' in country_code:
        country_code, subdiv = country_code.split('-', 1)
    return holidays.country_holidays(country_code, subdiv=subdiv)


class ExtraHolidays:
    """Thread-safe LRU cache of resolved ExtraHoliday country codes, keyed by (month, year)."""

    def __init__(self, cache_size: int = CACHE_SIZE) -> None:
        self._cache_size = cache_size
        self.cache: OrderedDict[tuple[int, int], dict[KrmDay, list[str]]] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, month: int, year: int) -> dict[KrmDay, list[str]]:
        key = (month, year)
        with self.lock:
            if key in self.cache:
                # Move accessed key to the end (marked as most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
        # Query outside the lock so a fetch does not serialise access to other months:
        # two threads may occasionally fetch the same month concurrently, last write wins.
        value = self._fetch(month, year)
        self.set(month, year, value)
        return value

    def set(self, month: int, year: int, value: dict[KrmDay, list[str]]) -> None:
        key = (month, year)
        with self.lock:
            if key in self.cache:
                # Update and move to end
                self.cache.move_to_end(key)
            self.cache[key] = value

            # Check if we exceeded the size limit
            if len(self.cache) > self._cache_size:
                # popitem(last=False) removes the first (oldest) item
                self.cache.popitem(last=False)

    def clear(self) -> None:
        with self.lock:
            self.cache.clear()

    @staticmethod
    def _fetch(month: int, year: int) -> dict[KrmDay, list[str]]:
        from krm3.core.models import ExtraHoliday  # imported lazily to avoid circular import with core.models

        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, calendar.monthrange(year, month)[1])
        return ExtraHoliday.objects.resolve(first, last)

    def is_holiday(self, day: datetime.date, contract: 'Contract | None' = None) -> bool:
        """Check whether the day is an extra holiday for the contract's country calendar."""
        calendar_code = (
            settings.HOLIDAYS_CALENDAR
            if contract is None
            else (contract.country_calendar_code or settings.HOLIDAYS_CALENDAR)
        )

        codes = self.get(day.month, day.year).get(KrmDay(day), [])

        return calendar_code in codes or (len(calendar_code) > 2 and calendar_code[:2] in codes)


extra_holidays = ExtraHolidays()
