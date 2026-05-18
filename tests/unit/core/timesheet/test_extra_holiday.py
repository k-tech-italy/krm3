import pytest
from django.core.exceptions import ValidationError

from krm3.core.models import ExtraHoliday
from testutils.date_utils import _dt
from contextlib import nullcontext as does_not_raise

dt_order = pytest.raises(ValidationError, match='End date must be at least one day after start date')
no_inf = pytest.raises(ValidationError, match='Open-ended period not supported')

@pytest.mark.parametrize(
    'period, expectation', [
        pytest.param(('2020-01-01', '2020-01-02'), does_not_raise(), id='OK'),
        pytest.param(('2020-01-02', '2020-01-02'), dt_order, id='NOK'),
        pytest.param((None, '2020-01-02'), no_inf, id='no-lower-inf'),
        pytest.param(('2020-01-01', None), no_inf, id='no-upper-inf'),
    ]
)
def test_extra_holiday_boundaries(period, expectation):
    with expectation:
        lower, upper = _dt(period[0]) if period[0] else None, _dt(period[1]) if period[1] else None
        ExtraHoliday.objects.create(country_codes=['IT'], period=(lower, upper), reason='any')
        period = ExtraHoliday.objects.first().period
        assert period.lower, period.upper == (lower, upper)
