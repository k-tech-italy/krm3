from contextlib import nullcontext as does_not_raise
from decimal import Decimal

import pytest
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
    'logged_hours, due_hours, expected',
    [
        pytest.param(4, 8, False, id='missing-hours'),
        pytest.param(8, 8, True, id='exact-hours'),
        pytest.param(9, 8, True, id='overtime'),
    ],
)
def test_fulfills_due_hours_with_worked_hours(logged_hours, due_hours, expected):
    entry = DayEntryFactory(day_hours=logged_hours)

    assert entry.fulfills_due_hours(Decimal(due_hours)) is expected


def test_fulfills_due_hours_with_other_hour_types():
    entry = DayEntryFactory(
        day_hours=1,
        on_call_hours=1,
        bank=-1,
        leave_hours=1,
        special_leave_hours=2,
        rest_hours=2,
    )

    assert entry.fulfills_due_hours(Decimal(8)) is True


@pytest.mark.parametrize('absence', ['is_sick', 'asked_holiday'])
def test_absence_fulfills_due_hours(absence):
    entry = DayEntryFactory(**{absence: True})

    assert entry.fulfills_due_hours(Decimal(8)) is True
