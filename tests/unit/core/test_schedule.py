import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from testutils.factories import ContractFactory, WorkScheduleFactory, MealVoucherThresholdsFactory


@pytest.mark.django_db
def test_work_schedule_validation_hours_range():
    ws = WorkScheduleFactory.build(hours=[Decimal(-1)] * 7)
    with pytest.raises(ValidationError, match='All hours must be between 0 and 24'):
        ws.save()

    ws = WorkScheduleFactory.build(hours=[Decimal(25)] * 7)
    with pytest.raises(ValidationError, match='All hours must be between 0 and 24'):
        ws.save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'date, expected',
    [
        pytest.param(datetime.date(2026, 1, 5), Decimal('8.0'), id='monday'),
        pytest.param(datetime.date(2026, 1, 9), Decimal('4.0'), id='friday'),
        pytest.param(datetime.date(2026, 1, 11), Decimal('0.0'), id='sunday'),
    ],
)
def test_work_schedule_get_hours_for_day(date, expected):
    hours = [
        Decimal('8.0'),
        Decimal('8.0'),
        Decimal('8.0'),
        Decimal('8.0'),
        Decimal('4.0'),
        Decimal('0.0'),
        Decimal('0.0'),
    ]
    ws = WorkScheduleFactory(hours=hours)
    assert ws.get_hours_for_day(date) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    'date, expected',
    [
        pytest.param(datetime.date(2026, 1, 1), Decimal('4.0'), id='holiday'),
        pytest.param(datetime.date(2026, 1, 2), Decimal('6.0'), id='working-day'),
        pytest.param(datetime.date(2026, 1, 4), Decimal('2.0'), id='sunday'),
    ],
)
def test_meal_voucher_thresholds_get_hours_for_day(date, expected):
    hours = [
        Decimal('6.0'),
        Decimal('6.0'),
        Decimal('6.0'),
        Decimal('6.0'),
        Decimal('6.0'),
        Decimal('2.0'),
        Decimal('2.0'),
    ]
    contract = ContractFactory(
        country_calendar_code='PL', meal_voucher_thresholds=MealVoucherThresholdsFactory(hours=hours)
    )
    mvt = contract.meal_voucher_thresholds

    assert mvt.get_hours_for_day(date) == expected
