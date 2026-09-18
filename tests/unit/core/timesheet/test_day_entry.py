from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from ktcalendars import KTDay
from ktcalendars.utils import dt

from testutils.factories import ContractFactory, DayEntryFactory


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
        country_calendar_code='IT-RM',
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
                    'Total hours would become 5.00 which is below scheduled hours'
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
                    'Invalid day entry for 2026-09-07: Cannot withdraw bank hours when task hours '
                    r'\(11.00\) are higher or equal scheduled hours'
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
