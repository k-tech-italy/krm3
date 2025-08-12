from contextlib import nullcontext as does_not_raise
import datetime

from dateutil.relativedelta import relativedelta
import freezegun
import pytest

from krm3.utils.dates import KrmDay, dt, KrmCalendar


class TestKrmDay:
    @pytest.mark.parametrize(
        'krm_day, prop, expected',
        [
            ('2025-06-02', 'date', dt('2025-06-02')),
            ('2025-06-02', 'day', 2),
            ('2025-06-02', 'month', 6),
            ('2025-06-02', 'year', 2025),
            ('2025-06-02', 'day_of_week_short', 'Mon'),
            ('2025-06-02', 'day_of_week', 'Monday'),
            ('2025-06-02', 'month_name_short', 'Jun'),
            ('2025-06-02', 'month_name', 'June'),
            ('2025-06-02', 'day_of_year', 153),
            ('2025-12-31', 'day_of_year', 365),
            ('2025-01-01', 'week_of_year', 1),
            ('2025-12-28', 'week_of_year', 52),
            # Note how we are in first week of next year
            ('2025-12-29', 'week_of_year', 1),
        ],
    )
    def test_properties(self, krm_day, prop, expected):
        assert getattr(KrmDay(krm_day), prop) == expected

    def test_equals(self):
        assert KrmDay('2025-06-02') == KrmDay('2025-06-02')
        assert KrmDay('2025-06-02') != KrmDay('2025-06-03')

    def test_gt(self):
        assert (KrmDay('2025-06-02') > KrmDay('2025-06-02')) is False
        assert (KrmDay('2025-06-03') > KrmDay('2025-06-02')) is True
        assert (KrmDay('2025-06-01') >= KrmDay('2025-06-02')) is False
        assert (KrmDay('2025-06-02') >= KrmDay('2025-06-02')) is True
        assert (KrmDay('2025-06-03') >= KrmDay('2025-06-02')) is True

    def test_lt(self):
        assert (KrmDay('2025-06-02') < KrmDay('2025-06-02')) is False
        assert (KrmDay('2025-06-02') < KrmDay('2025-06-03')) is True
        assert (KrmDay('2025-06-02') <= KrmDay('2025-06-01')) is False
        assert (KrmDay('2025-06-02') <= KrmDay('2025-06-02')) is True
        assert (KrmDay('2025-06-02') <= KrmDay('2025-06-03')) is True

    def test_sub(self):
        assert KrmDay('2025-06-02') - KrmDay('2025-06-02') == 0
        assert KrmDay('2024-02-28') - KrmDay('2024-03-01') == -2
        assert KrmDay('2024-03-01') - KrmDay('2024-02-28') == +2

    def test_add_days(self):
        assert KrmDay('2024-02-28') + 2 == KrmDay('2024-03-01')

    def test_add_stdlib_timedelta(self):
        assert KrmDay('2024-02-28') + datetime.timedelta(days=2) == KrmDay('2024-03-01')

    def test_add_stdlib_timedelta_ignoring_finer_granularity_than_day(self):
        assert KrmDay('2024-02-28') + datetime.timedelta(days=2, hours=14, seconds=10) == KrmDay('2024-03-01')

    def test_add_relativedelta(self):
        assert KrmDay('2024-02-28') + relativedelta(months=1) == KrmDay('2024-03-28')
        assert KrmDay('2024-02-28') + relativedelta(years=1, months=-1, days=+1) == KrmDay('2025-01-29')
        assert KrmDay('2024-02-28') + relativedelta(weeks=1) == KrmDay('2024-03-06')
        assert KrmDay('2024-02-28') + relativedelta(years=-1, weeks=2) == KrmDay('2023-03-14')

    def test_add_relativedelta_ignoring_finer_granularity_than_day(self):
        assert KrmDay('2024-02-28') + relativedelta(months=1, hours=23, minutes=30, seconds=45) == KrmDay('2024-03-28')

    def test_add_relativedelta_ignoring_absolute_information(self):
        assert KrmDay('2024-02-28') + relativedelta(months=1, day=23, month=3, year=1945) == KrmDay('2024-03-28')

    def test_hash(self):
        assert hash(KrmDay('2025-06-02')) == hash(KrmDay('2025-06-02'))
        assert hash(KrmDay('2025-06-02')) != hash(KrmDay('2025-06-03'))
        assert hash(KrmDay('2025-06-02')) == 20250602

    def test_range_to(self):
        assert list(KrmDay('2024-02-28').range_to(datetime.date(2024, 3, 1))) == [
            KrmDay('2024-02-28'),
            KrmDay('2024-02-29'),
            KrmDay('2024-03-01'),
        ]
        assert list(KrmDay('2024-02-28').range_to(KrmDay('2024-03-01'))) == [
            KrmDay('2024-02-28'),
            KrmDay('2024-02-29'),
            KrmDay('2024-03-01'),
        ]

    @freezegun.freeze_time('2025-03-02')
    def test_today(self):
        assert KrmDay() == KrmDay('2025-03-02')

    def test_init(self):
        assert KrmDay('2025-06-02') == KrmDay(dt('2025-06-02'))
        assert KrmDay('2025-06-02') == KrmDay(KrmDay('2025-06-02'))

    def test_is_holiday(self):
        assert KrmDay('2025-06-02').is_holiday() is True  # Bank Hol in Italy
        assert KrmDay('2023-06-29').is_holiday() is True  # Bank Hol in Rome
        assert KrmDay('2025-08-25').is_holiday() is False  # Bank Hol in UK
        assert KrmDay('2025-06-07').is_holiday() is False  # Sat
        assert KrmDay('2025-06-08').is_holiday() is True  # Sun

        assert KrmDay('2025-08-25').is_holiday(country_calendar='GB-ENG') is True  # Bank Hol in UK
        assert KrmDay('2025-03-17').is_holiday(country_calendar='GB-ENG') is False  # St Patrick's day
        assert KrmDay('2025-03-17').is_holiday(country_calendar='GB-NIR') is True  # St Patrick's day


class TestKrmCalendar:
    def test_itermonthdates(self):
        cal = KrmCalendar()
        assert [kd.day for kd in cal.itermonthdates(2025, 6)] == (
            list(range(26, 32)) + list(range(1, 31)) + list(range(1, 7))
        )

    def test_itermonthdays(self):
        cal = KrmCalendar()
        assert [kd.day if kd else None for kd in cal.itermonthdays(2025, 6)] == (
            [None for _ in range(26, 32)] + list(range(1, 31)) + [None for _ in range(1, 7)]
        )

    @pytest.mark.parametrize(
        'start, end, expectation, result',
        [
            ('2025-06-02', '2025-06-02', does_not_raise(), ['2025-06-02']),
            ('2025-06-02', '2025-06-01', pytest.raises(ValueError, match='Start date cannot be after end date.'), None),
            ('2024-02-28', '2024-03-01', does_not_raise(), ['2024-02-28', '2024-02-29', '2024-03-01']),
        ],
    )
    def test_iter_dates(self, start, end, expectation, result):
        cal = KrmCalendar()
        with expectation:
            assert list(cal.iter_dates(start, end)) == [KrmDay(x) for x in result]

    @pytest.mark.parametrize(
        'krm_day, expected',
        [
            pytest.param('2024-02-28', (KrmDay('2024-02-26'), KrmDay('2024-03-03')), id='explicit_date'),
            pytest.param(None, (KrmDay('2024-02-26'), KrmDay('2024-03-03')), id='none'),
        ],
    )
    @freezegun.freeze_time('2024-02-26')
    def test_week_for(self, krm_day, expected):
        assert KrmCalendar().week_for(KrmDay(krm_day)) == expected

    @pytest.mark.parametrize(
        'krm_day, expected',
        [
            ('2024-02-28', [KrmDay('2024-02-26') + i for i in range(7)]),
            (None, [KrmDay('2024-02-26') + i for i in range(7)]),
        ],
    )
    @freezegun.freeze_time('2024-02-26')
    def test_iter_week(self, krm_day, expected):
        assert list(KrmCalendar().iter_week(krm_day)) == expected


    @pytest.mark.parametrize(
        'start, end, expectation, result',
        [
            ('2025-07-11', '2025-07-15', does_not_raise(), ['2025-07-11', '2025-07-14', '2025-07-15']),
            ('2025-07-11', '2025-07-13', does_not_raise(), ['2025-07-11']),
            ('2025-07-12', '2025-07-13', does_not_raise(), []),
            ('2025-06-01', '2025-06-03', does_not_raise(), ['2025-06-03']), # 2025-06-02 italian bank holiday
            ('2025-06-02', '2025-06-01', pytest.raises(ValueError, match='Start date cannot be after end date.'), None)
        ],
    )
    def test_get_work_days(self, start, end, expectation, result):
        cal = KrmCalendar()
        with expectation:
            assert cal.get_work_days(start, end) == [KrmDay(x) for x in result]
