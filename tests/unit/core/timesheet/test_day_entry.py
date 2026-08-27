import pytest
from ktcalendars import KTDay
from ktcalendars.utils import dt

from testutils.factories import ContractFactory, DayEntryFactory

from contextlib import nullcontext as does_not_raise

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