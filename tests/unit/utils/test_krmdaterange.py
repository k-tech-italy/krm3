import datetime
from contextlib import nullcontext as does_not_raise

import pytest

from krm3.utils.dates import KrmDateRange, KrmDay
from testutils.date_utils import _dt

param_order = pytest.raises(ValueError, match='Lower bound must be smaller than upper bound')
ok = does_not_raise()
non_iterable = pytest.raises(TypeError, match='Cannot iterate over unbounded range')


def test_boundaries():
    period = KrmDateRange('2026-01-01', '2026-01-31')
    assert tuple(x for x in period.boundaries) == (_dt('2026-01-01'), _dt('2026-01-31'))


@pytest.mark.parametrize(
    'period, expectation, result',
    [
        pytest.param(('2026-01-01', '2026-01-03'), ok, ['2026-01-01', '2026-01-02'], id='ok'),
        pytest.param((None, '2026-01-03'), non_iterable, None, id='none-start'),
        pytest.param(('2026-01-01', None), non_iterable, None, id='none-end'),
        pytest.param((datetime.date.min, '2026-01-03'), non_iterable, None, id='min-start'),
        pytest.param(('2026-01-01', datetime.date.max), non_iterable, None, id='max-end'),
    ]
)
def test_iterate(period, expectation, result):
    kdr = KrmDateRange(*period)
    with expectation:
        assert [x for x in kdr] == result


@pytest.mark.parametrize(
    'period, expectation, bounds, isempty',
    [
        pytest.param(
            ('2026-01-01', _dt('2026-01-31')),
            ok,
            (_dt('2026-01-01'), _dt('2026-01-31')),
            False,
            id='simple',
        ),
        pytest.param((_dt('2026-01-01'), None), ok, (_dt('2026-01-01'), None), False, id='none-end'),
        pytest.param(
            (KrmDay('2026-01-01'), datetime.date.max),
            ok,
            (_dt('2026-01-01'), datetime.date.max),
            False,
            id='max-end',
        ),
        pytest.param((None, '2026-01-01'), ok, (None, _dt('2026-01-01')), False, id='none-start'),
        pytest.param((None,), ok, (None, None), False, id='one'),
        pytest.param((), ok, (None, None), False, id='empty'),
        pytest.param(
            (datetime.date.min, datetime.date.max),
            ok,
            (datetime.date.min, datetime.date.max),
            False,
            id='min-max',
        ),
        pytest.param(('2026-02-03', '2026-02-01'), param_order, None, False, id='order'),
        pytest.param(
            ('2026-02-01', '2026-02-01'), ok, (_dt('2026-02-01'), _dt('2026-02-01')), False, id='one-day'
        ),
    ],
)
def test_instance_creation(period, expectation, bounds, isempty):
    with expectation:
        dr = KrmDateRange(*period)
        assert dr is not None
        assert (dr.lower, dr.upper) == bounds
        assert dr.isempty is isempty


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-01-01', '2026-01-31'), ('2026-02-01', None), True, id='fully-lt'),
        pytest.param(('2026-01-01', '2026-02-02'), ('2026-02-01', '2026-02-10'), False, id='overlap-lower'),
    ],
)
def test_fully_before(period, other, result):
    assert KrmDateRange(*period).fully_lt(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-01', '2026-01-31'), True, id='fully-gt'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-01', None), False, id='open-ended'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-01', '2026-02-02'), False, id='overlap-upper'),
    ],
)
def test_fully_after(period, other, result):
    assert KrmDateRange(*period).fully_gt(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, other, before, after',
    [
        pytest.param(('2026-01-01', None), ('2026-01-01', None), False, False, id='lower-equal'),
        pytest.param(('2026-01-01', None), ('2026-01-02', None), True, False, id='lower-lt'),
        pytest.param(('2026-01-02', None), ('2026-01-01', None), False, True, id='lower-gt'),
    ],
)
def test_start_comparison(period, other, before: bool, after: bool):
    assert KrmDateRange(*period).startsbefore(KrmDateRange(*other)) is before
    assert KrmDateRange(*period).startsafter(KrmDateRange(*other)) is after


@pytest.mark.parametrize(
    'period, other, before, after',
    [
        pytest.param(('2026-01-01', '2026-01-10'), ('2026-01-02', '2026-01-10'), False, False, id='equal'),
        pytest.param(('2026-01-01', None), ('2026-01-02', None), False, False, id='equal-none'),
        pytest.param(('2026-01-01', None), ('2026-01-01', '2026-01-10'), False, True, id='none'),
        pytest.param(('2026-01-01', '2026-01-10'), ('2026-01-01', '2026-01-11'), True, False, id='lower'),
        pytest.param(('2026-01-01', '2026-01-10'), ('2026-01-01', '2026-01-09'), False, True, id='higher'),
    ],
)
def test_end_comparison(period, other, before: bool, after: bool):
    assert KrmDateRange(*period).endsbefore(KrmDateRange(*other)) is before
    assert KrmDateRange(*period).endsafter(KrmDateRange(*other)) is after


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-01-01', '2026-02-01'), ('2026-02-01', '2026-02-10'), True, id='precedes'),
        pytest.param(('2026-01-01', '2026-01-31'), ('2026-02-02', '2026-02-10'), False, id='gap-left'),
        pytest.param(('2026-01-01', None), ('2026-02-01', '2026-02-10'), False, id='none'),
    ],
)
def test_precedes(period, other, result):
    assert KrmDateRange(*period).precedes(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-01', '2026-02-01'), True, id='succeeds'),
        pytest.param(('2026-02-02', '2026-02-28'), ('2026-01-02', '2026-01-31'), False, id='gap-right'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-01', None), False, id='none'),
    ],
)
def test_succeed(period, other, result):
    assert KrmDateRange(*period).follows(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, day, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), '2026-02-01', True, id='in'),
        pytest.param(('2026-02-02', '2026-02-28'), '2026-02-01', False, id='left'),
        pytest.param(('2026-02-01', '2026-02-28'), '2026-02-28', False, id='right'),
        pytest.param(('2026-02-01', None), '2026-02-28', True, id='none'),
    ],
)
def test_includes(period, day, result):
    assert (_dt(day) in KrmDateRange(*period)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', '2026-02-28'), True, id='same'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-01-31', '2026-02-28'), False, id='left'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', '2026-03-01'), False, id='right'),
        pytest.param((None, '2026-02-28'), ('2026-02-01', '2026-02-28'), True, id='self-lower-None'),
        pytest.param(('2026-02-01', None), ('2026-02-01', '2026-02-28'), True, id='self-upper-none'),
        pytest.param(('2026-02-01', None), ('2026-02-01', '2026-02-28'), True, id='self-upper-none'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', None), False, id='other-upper-none'),
    ],
)
def test_contains(period, other, result):
    assert KrmDateRange(*period).contains(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', '2026-02-28'), True, id='same'),
        pytest.param(('2026-02-05', '2026-02-20'), ('2026-02-01', '2026-02-28'), True, id='inside'),
        pytest.param(('2026-02-01', '2026-02-20'), ('2026-02-01', '2026-02-28'), True, id='same-lower'),
        pytest.param(('2026-02-05', '2026-02-28'), ('2026-02-01', '2026-02-28'), True, id='same-upper'),
        pytest.param(('2026-01-31', '2026-02-20'), ('2026-02-01', '2026-02-28'), False, id='wider-left'),
        pytest.param(('2026-02-05', '2026-03-01'), ('2026-02-01', '2026-02-28'), False, id='wider-right'),
        pytest.param(('2026-01-31', '2026-03-01'), ('2026-02-01', '2026-02-28'), False, id='wider-both'),
        pytest.param(('2026-02-01', None), ('2026-02-01', '2026-02-28'), False, id='self-upper-none'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', None), True, id='other-upper-none'),
        pytest.param((None, '2026-02-28'), ('2026-02-01', '2026-02-28'), False, id='self-lower-none'),
        pytest.param(('2026-02-01', '2026-02-28'), (None, '2026-02-28'), True, id='other-lower-none'),
        pytest.param((None, '2026-02-28'), (None, '2026-02-28'), True, id='both-lower-none'),
    ],
)
def test_contained_by(period, other, result):
    assert KrmDateRange(*period).contained_by(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, day, result',
    [
        pytest.param(('2026-02-01', '2026-03-01'), '2026-02-01', True, id='lower'),
        pytest.param(('2026-02-01', '2026-03-01'), _dt('2026-02-28'), True, id='upper'),
        pytest.param(('2026-02-01', '2026-03-01'), KrmDay('2026-01-31'), False, id='lower-'),
        pytest.param(('2026-02-01', '2026-03-01'), '2026-03-01', False, id='upper+'),
    ],
)
def test_in(period, day, result):
    assert (day in KrmDateRange(*period)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', '2026-02-28'), True, id='same'),
        pytest.param(('2026-02-05', '2026-02-20'), ('2026-02-01', '2026-02-28'), True, id='self-inside-other'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-05', '2026-02-20'), True, id='other-inside-self'),
        pytest.param(('2026-02-01', '2026-02-15'), ('2026-01-15', '2026-02-28'), True, id='self-lower-in-other'),
        pytest.param(('2026-01-15', '2026-02-28'), ('2026-02-01', '2026-02-15'), True, id='other-upper-in-self'),
        pytest.param(('2026-02-01', None), ('2026-02-01', '2026-02-28'), True, id='self-upper-none'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', None), True, id='other-upper-none'),
        pytest.param(('2026-01-01', '2026-01-31'), ('2026-02-01', '2026-02-28'), False, id='gap'),
        pytest.param(('2026-01-01', '2026-02-01'), ('2026-02-01', '2026-02-28'), False, id='adjacent'),
    ],
)
def test_overlaps(period, other, result):
    assert KrmDateRange(*period).overlap(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, other, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-28', '2026-03-15'), True, id='self-precedes-other'),
        pytest.param(('2026-02-28', '2026-03-15'), ('2026-02-01', '2026-02-28'), True, id='self-follows-other'),
        pytest.param(('2026-01-01', '2026-02-01'), ('2026-02-01', '2026-02-28'), True, id='adjacent-boundary'),
        pytest.param(('2026-01-01', '2026-01-31'), ('2026-02-01', '2026-02-28'), False, id='gap'),
        pytest.param(('2026-01-01', '2026-02-01'), ('2026-02-02', '2026-02-28'), False, id='not-adjacent-gap'),
        pytest.param(('2026-02-01', '2026-02-28'), ('2026-02-01', '2026-02-28'), False, id='same-not-adjacent'),
    ],
)
def test_adjacent_to(period, other, result):
    assert KrmDateRange(*period).adjacent_to(KrmDateRange(*other)) is result


@pytest.mark.parametrize(
    'period, result',
    [
        pytest.param(('2026-02-01', '2026-02-28'), '[2026-02-01:2026-02-28)',  id='ok'),
        pytest.param((None, '2026-02-28'), '(...:2026-02-28)',  id='none-start'),
        pytest.param(('2026-02-01', None), '[2026-02-01:...)',  id='none-end'),
        pytest.param((datetime.date.min, '2026-02-28'), '(...:2026-02-28)', id='inf-start'),
        pytest.param(('2026-02-01', datetime.date.max), '[2026-02-01:...)', id='inf-end'),
    ],
)
def test_str(period, result):
    res = str(KrmDateRange(*period))
    assert res == result, f'Expected {result}, got {res}'
