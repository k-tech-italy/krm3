from contextlib import nullcontext as does_not_raise
import datetime
import pytest

from krm3.utils.dates import KrmDay, dt, KrmCalendar


class TestKrmDay:
    @pytest.mark.parametrize(
        "krm_day, prop, expected", [
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
            ('2025-06-02', 'is_holiday', True),  # Mon
            ('2025-06-29', 'is_holiday', True),  # Rome Saint's
            ('2025-06-03', 'is_holiday', False),  # Tue
            ('2025-06-07', 'is_holiday', False),  # Sat
            ('2025-06-08', 'is_holiday', True),  # Sun
        ]
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

    def test_add(self):
        assert KrmDay('2024-02-28') + 2  == KrmDay('2024-03-01')

    def test_hash(self):
        assert hash(KrmDay('2025-06-02')) == hash(KrmDay('2025-06-02'))
        assert hash(KrmDay('2025-06-02')) != hash(KrmDay('2025-06-03'))
        assert hash(KrmDay('2025-06-02')) == 20250602

    def test_reladd(self):
        assert KrmDay('2024-02-28').reladd(2) == KrmDay('2024-03-01')
        assert KrmDay('2024-02-28').reladd(months=1) == KrmDay('2024-03-28')
        assert KrmDay('2024-02-28').reladd(years=1, months=-1, days=+1) == KrmDay('2025-01-29')

    def test_range_to(self):
        assert list(KrmDay('2024-02-28').range_to(datetime.date(2024, 3, 1))) == [
            KrmDay('2024-02-28'), KrmDay('2024-02-29'), KrmDay('2024-03-01')
        ]
        assert list(KrmDay('2024-02-28').range_to(KrmDay('2024-03-01'))) == [
            KrmDay('2024-02-28'), KrmDay('2024-02-29'), KrmDay('2024-03-01')
        ]


class TestKrmCalendar:
    def test_itermonthdates(self):
        cal = KrmCalendar()
        assert [kd.day for kd in cal.itermonthdates(2025, 6)] == \
               [x for x in range(26, 32)] + [x for x in range(1, 31)] + [x for x in range(1, 7)]  # noqa: C416

    def test_itermonthdays(self):
        cal = KrmCalendar()
        assert [kd.day if kd else None for kd in cal.itermonthdays(2025, 6)] == \
               [None for x in range(26, 32)] + [x for x in range(1, 31)] + [None for x in range(1, 7)]  # noqa: C416

    @pytest.mark.parametrize(
        "start, end, expectation, result", [
            ('2025-06-02', '2025-06-02', does_not_raise(), ['2025-06-02']),
            ('2025-06-02', '2025-06-01', pytest.raises(ValueError, match="Start date cannot be after end date."), None),
            ('2024-02-28', '2024-03-01', does_not_raise(), ['2024-02-28', '2024-02-29', '2024-03-01']),
        ]
    )
    def test_between(self, start, end, expectation, result):
        cal = KrmCalendar()
        with expectation:
            assert cal.between(start, end) == [KrmDay(x) for x in result]
