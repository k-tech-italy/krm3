from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
from constance.test import override_config
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from ktcalendars import KTDay
from ktcalendars.utils import dt

from testutils.factories import ContractFactory, DayEntryFactory, TaskEntryFactory, TaskFactory


@pytest.mark.parametrize(
    'day, expectation',
    [
        pytest.param(dt('2026-06-29'), does_not_raise(), id='within-contract-period'),
        pytest.param(
            dt('2027-01-01'),
            pytest.raises(ValueError, match='Date outside contract period'),
            id='outside-contract-period',
        ),
    ],
)
def test_get_ktday_uses_contract_calendar(day, expectation):
    contract = ContractFactory(
        base_in__country__country_calendar_code='IT',
        base_in__subdivision_code='RM',
        period=(dt('2026-01-01'), dt('2027-01-01')),
    )
    day_entry = DayEntryFactory(
        day=day,
        contract=contract,
        resource=contract.resource,
    )

    with expectation:
        result = day_entry.get_ktday()

        assert isinstance(result, KTDay)
        assert result.date == day
        assert result.ktcalendar.country_calendar_code == 'IT-RM'


@pytest.mark.parametrize(
    'worked_hours, bank, expectation',
    [
        pytest.param(
            '8.00',
            '3.00',
            pytest.raises(
                ValidationError,
                match=(
                    'Invalid day entry for 2026-09-07: Cannot deposit 3.00 bank hours. '
                    'Total hours would become 5.00, which is below scheduled hours'
                ),
            ),
            id='deposit-below-scheduled-hours',
        ),
        pytest.param('10.00', '2.00', does_not_raise(), id='deposit-up-to-scheduled-hours'),
        pytest.param(
            '8.00',
            '-3.00',
            pytest.raises(
                ValidationError,
                match=(
                    'Invalid day entry for 2026-09-07: Cannot withdraw bank hours when effective hours '
                    r'\(11.00\) are higher than scheduled hours'
                ),
            ),
            id='withdrawal-above-scheduled-hours',
        ),
        pytest.param('6.00', '-2.00', does_not_raise(), id='withdrawal-up-to-scheduled-hours'),
    ],
)
def test_verify_bank_hours_against_scheduled_hours(worked_hours, bank, expectation):
    day_entry = DayEntryFactory.build(
        day=dt('2026-09-07'),
        day_hours=Decimal(worked_hours),
        due_hours=Decimal('8.00'),
        bank=Decimal(bank),
    )

    with expectation:
        day_entry.verify_bank_hours_against_scheduled_hours()


def test_effective_hours_include_absences_and_bank_operations():
    day_entry = DayEntryFactory.build(
        day_hours=Decimal('2.00'),
        leave_hours=Decimal('2.00'),
        special_leave_hours=Decimal('1.00'),
        rest_hours=Decimal('1.00'),
        bank=Decimal('-2.00'),
    )

    assert day_entry.effective_hours == Decimal('8.00')


@pytest.mark.parametrize(
    ('worked_hours', 'bank', 'due_hours', 'expected'),
    (
        pytest.param('2.00', '4.00', '8.00', '0.00', id='minimum-zero'),
        pytest.param('6.00', '0.00', '8.00', '6.00', id='within-limits'),
        pytest.param('10.00', '0.00', '8.00', '8.00', id='maximum-due-hours'),
    ),
)
def test_regular_hours_are_clamped_between_zero_and_due_hours(worked_hours, bank, due_hours, expected):
    day_entry = DayEntryFactory.build(
        day_hours=Decimal(worked_hours),
        night_hours=Decimal('0.00'),
        travel_hours=Decimal('0.00'),
        bank=Decimal(bank),
        due_hours=Decimal(due_hours),
    )

    assert day_entry.regular_hours == Decimal(expected)


@pytest.mark.parametrize(
    'absence_data',
    (
        pytest.param({'is_sick': True}, id='sick'),
        pytest.param({'asked_holiday': True}, id='requested-holiday'),
    ),
)
def test_task_entry_cannot_be_created_during_full_day_absence(absence_data):
    day_entry = DayEntryFactory(**absence_data)

    with pytest.raises(ValidationError, match='Task entries cannot be added'):
        TaskEntryFactory(day_entry=day_entry)


def test_resource_cannot_have_two_day_entries_on_the_same_day():
    day_entry = DayEntryFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        DayEntryFactory(resource=day_entry.resource, contract=day_entry.contract, day=day_entry.day)


@pytest.mark.parametrize(
    ('worked_hours', 'bank', 'expected'),
    [
        pytest.param(5, 0, 1, id='no-bank'),
        pytest.param(5, 1, 0, id='deposit-covers-extra-hours'),
        pytest.param(5, Decimal('0.5'), Decimal('0.5'), id='partial-deposit'),
        pytest.param(6, 1, 1, id='deposit-and-overtime'),
        pytest.param(3, -1, 0, id='withdrawal'),
    ],
)
def test_bank_deposit_is_not_overtime(worked_hours, bank, expected):
    contract = ContractFactory(
        period=(dt('2026-01-01'), None),
        working_schedule={'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0},
    )
    day_entry = DayEntryFactory(
        day=dt('2026-09-02'),
        contract=contract,
        resource=contract.resource,
        due_hours=Decimal(4),
        bank=Decimal(bank),
    )
    task = TaskFactory(resource=contract.resource, period=contract.period)
    TaskEntryFactory(day_entry=day_entry, task=task, day_shift_hours=worked_hours)

    day_entry.refresh(task_entries=None, drop_existing=False)

    assert day_entry.overtime_hours == expected


def _deposit_entry(contract, day, bank):
    return DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=dt(day),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal(bank),
    )


def test_allows_logging_ordinary_hours_when_balance_is_already_above_the_limit():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    for day in ('2026-09-07', '2026-09-08', '2026-09-09'):
        _deposit_entry(contract, day, '8.00')
    assert contract.resource.get_bank_hours_balance(dt('2026-09-30')) == Decimal('24.00')

    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-10'),
        day_hours=Decimal('8.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('0.00'),
    )

    day_entry.full_clean()


def test_allows_updating_an_entry_without_changing_the_balance_when_balance_is_above_the_limit():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    for day in ('2026-09-07', '2026-09-08', '2026-09-09'):
        day_entry = _deposit_entry(contract, day, '8.00')

    day_entry.comment = 'just a note'

    day_entry.full_clean()
    day_entry.save()


def test_rejects_deposit_exceeding_upper_bound():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    _deposit_entry(contract, '2026-09-07', '8.00')
    _deposit_entry(contract, '2026-09-14', '8.00')

    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-21'),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('1.00'),
    )

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the maximum bank balance of 16.0 hours. '
            'Current balance: 16.00, attempting to add: 1.00'
        ),
    ):
        day_entry.full_clean()


def test_rejects_withdrawal_below_lower_bound():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    _deposit_entry(contract, '2026-09-07', '-8.00')
    _deposit_entry(contract, '2026-09-14', '-8.00')

    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-21'),
        day_hours=Decimal('0.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('-1.00'),
    )

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the minimum bank balance of -16.0 hours. '
            'Current balance: -16.00, attempting to change by: -1.00'
        ),
    ):
        day_entry.full_clean()


def test_rejects_retroactive_entry_rebuilding_the_curve_out_of_range():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    _deposit_entry(contract, '2026-09-07', '8.00')
    _deposit_entry(contract, '2026-09-14', '8.00')

    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-10'),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('1.00'),
    )

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the maximum bank balance of 16.0 hours. '
            'Current balance: 8.00, attempting to add: 1.00'
        ),
    ):
        day_entry.full_clean()


@override_config(BANK_HOURS_UPPER_BOUND=32.0)
def test_rejects_increasing_an_existing_deposit_when_a_later_balance_exceeds_the_bound():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    _deposit_entry(contract, '2026-09-01', '8.00')
    _deposit_entry(contract, '2026-09-02', '8.00')
    changed = _deposit_entry(contract, '2026-09-07', '4.00')
    _deposit_entry(contract, '2026-09-08', '8.00')
    _deposit_entry(contract, '2026-09-09', '4.00')
    assert contract.resource.get_bank_hours_balance(dt('2026-09-30')) == Decimal('32.00')

    changed.bank = Decimal('8.00')

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the maximum bank balance of 32.0 hours. '
            'Current balance: 16.00, attempting to add: 4.00'
        ),
    ):
        changed.full_clean()


def test_rejects_a_temporary_excess_even_when_a_later_movement_restores_the_balance():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    _deposit_entry(contract, '2026-09-01', '8.00')
    _deposit_entry(contract, '2026-09-02', '8.00')
    _deposit_entry(contract, '2026-09-04', '-8.00')
    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-03'),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('8.00'),
    )

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the maximum bank balance of 16.0 hours. '
            'Current balance: 16.00, attempting to add: 8.00'
        ),
    ):
        day_entry.full_clean()


def test_allows_reducing_an_existing_deposit_when_the_rebuilt_curve_stays_within_the_bounds():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    changed = _deposit_entry(contract, '2026-09-01', '8.00')
    _deposit_entry(contract, '2026-09-02', '-8.00')
    _deposit_entry(contract, '2026-09-03', '-8.00')
    _deposit_entry(contract, '2026-09-04', '-4.00')
    assert contract.resource.get_bank_hours_balance(dt('2026-09-30')) == Decimal('-12.00')

    changed.bank = Decimal('4.00')

    changed.full_clean()


def test_rejects_moving_a_withdrawal_after_the_deposits_it_was_funding():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    withdrawal = DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-05'),
        day_hours=Decimal('0.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('-8.00'),
    )
    for day in ('2026-09-10', '2026-09-12', '2026-09-14'):
        _deposit_entry(contract, day, '8.00')
    assert contract.resource.get_bank_hours_balance(dt('2026-09-30')) == Decimal('16.00')

    withdrawal.day = dt('2026-09-16')

    with pytest.raises(
        ValidationError,
        match=(
            'This transaction would exceed the maximum bank balance of 16.0 hours. '
            'Current balance: 0, attempting to add: 0.00'
        ),
    ):
        withdrawal.full_clean()


def test_allows_moving_an_entry_when_the_curve_stays_within_the_limits():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    DayEntryFactory(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-05'),
        day_hours=Decimal('0.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('-8.00'),
    )
    for day in ('2026-09-10', '2026-09-12'):
        _deposit_entry(contract, day, '8.00')
    moved = _deposit_entry(contract, '2026-09-14', '8.00')

    moved.day = dt('2026-09-08')

    moved.full_clean()
    moved.save()
    assert moved.day == dt('2026-09-08')


@override_config(BANK_HOURS_UPPER_BOUND=32.0)
def test_allows_the_same_movement_when_the_bound_is_raised():
    contract = ContractFactory(period=(dt('2026-09-01'), dt('2026-10-01')))
    for day in ('2026-09-07', '2026-09-14'):
        _deposit_entry(contract, day, '8.00')

    day_entry = DayEntryFactory.build(
        resource=contract.resource,
        contract=contract,
        day=dt('2026-09-21'),
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal('8.00'),
    )

    day_entry.full_clean()
