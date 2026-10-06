from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from ktcalendars import KTDay
from ktcalendars.utils import dt

from testutils.factories import ContractFactory, DayEntryFactory, TaskEntryFactory


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
