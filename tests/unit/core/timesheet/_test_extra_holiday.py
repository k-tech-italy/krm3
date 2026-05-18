from contextlib import nullcontext as does_not_raise

import pytest
from django.core.exceptions import ValidationError
from psycopg.types.range import DateRange

from krm3.utils.dates import KrmDay
from testutils.date_utils import _dt
from testutils.factories import ExtraHolidayFactory

from krm3.core.models import ExtraHoliday

dt_order = pytest.raises(ValidationError, match='End date must be at least one day after start date')
no_inf = pytest.raises(ValidationError, match='Open-ended period not supported')


@pytest.mark.parametrize(
    'period, expectation',
    [
        pytest.param(('2020-01-01', '2020-01-02'), does_not_raise(), id='OK'),
        pytest.param(('2020-01-02', '2020-01-02'), dt_order, id='NOK'),
        pytest.param((None, '2020-01-02'), no_inf, id='no-lower-inf'),
        pytest.param(('2020-01-01', None), no_inf, id='no-upper-inf'),
    ],
)
def test_extra_holiday_boundaries(period, expectation):
    with expectation:
        lower, upper = _dt(period[0]) if period[0] else None, _dt(period[1]) if period[1] else None
        ExtraHoliday.objects.create(country_codes=['IT'], period=(lower, upper), reason='any')
        period = ExtraHoliday.objects.first().period
        assert period.lower, period.upper == (lower, upper)


@pytest.fixture
def extra_holidays():
    return [
        ExtraHolidayFactory(period=(_dt('2024-01-01'), _dt('2024-01-03')), country_codes=['IT-MI', 'UK']),
        ExtraHolidayFactory(period=(_dt('2024-06-10'), _dt('2024-06-11'))),
    ]


def test_extra_holiday_unnest(extra_holidays):
    result = list(ExtraHoliday.objects.unnested().values_list('country_code', 'country_codes', 'period'))
    from django.conf import settings

    assert result == [
        ('IT-MI', ['IT-MI', 'UK'], DateRange(_dt('2024-01-01'), _dt('2024-01-03'))),
        ('UK', ['IT-MI', 'UK'],  DateRange(_dt('2024-01-01'), _dt('2024-01-03'))),
        (settings.HOLIDAYS_CALENDAR, [settings.HOLIDAYS_CALENDAR],  DateRange(_dt('2024-06-10'), _dt('2024-06-11'))),
    ]


def test_extra_holiday_resolve(extra_holidays):
    from django.conf import settings

    result = ExtraHoliday.objects.resolve(from_date=_dt('2024-01-02'), to_date=_dt('2024-06-10'))

    assert result == {
        KrmDay('2024-01-02'): ['IT-MI', 'UK'],
        KrmDay('2024-06-10'): [settings.HOLIDAYS_CALENDAR]

    }
