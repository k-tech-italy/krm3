import datetime
import freezegun
from contextlib import nullcontext as does_not_raise

from krm3.timesheet import utils as timesheet_utils
import pytest

from testutils.factories import ResourceFactory, TaskFactory, TimeEntryFactory


@pytest.fixture
def time_entry_factory():
    def _make(**kwargs):
        return TimeEntryFactory(resource=ResourceFactory(), task=TaskFactory(), **kwargs)

    return _make


@freezegun.freeze_time(datetime.date(2024, 1, 1))
@pytest.mark.parametrize(
    ('date', 'expected_behavior'),
    (
        pytest.param(datetime.date(2024, 1, 1), does_not_raise(), id='same_day'),
        pytest.param(
            datetime.date(2024, 1, 2), pytest.raises(ValueError, match='belong to the same day'), id='different_days'
        ),
    ),
)
def test_verify_time_entries_from_same_day(date, expected_behavior, time_entry_factory):
    time_entry_for_today = time_entry_factory(date=datetime.date.today())
    other_time_entry = time_entry_factory(date=date)
    with expected_behavior:
        timesheet_utils.verify_time_entries_from_same_day((time_entry_for_today, other_time_entry))
