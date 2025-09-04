from datetime import date
import pytest
from django.core.exceptions import ValidationError
from testutils.factories import ExtraHolidayFactory

def test_extra_holiday_upper_bond_must_be_one_day_greater():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 1)
    with pytest.raises(ValidationError, match='End date must be at least one day after start date.'):
        ExtraHolidayFactory(period=(start_dt, end_dt))

def test_create_extra_holiday_with_correct_period():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 2)
    ExtraHolidayFactory(period=(start_dt, end_dt))
