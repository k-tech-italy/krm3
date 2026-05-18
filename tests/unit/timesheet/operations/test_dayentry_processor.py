import pytest

from krm3.timesheet.operations import DayEntryProcessor
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, TaskFactory


@pytest.fixture
def contract():
    return ContractFactory(
        working_schedule={'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0},
        meal_voucher={'mon': 2, 'tue': 3, 'wed': 2, 'thu': 2, 'fri': 2, 'sat': 1, 'sun': 2},
        sunday_as_holiday=True,
    )


@pytest.fixture
def tasks(contract):
    return [
        TaskFactory(resource=contract.resource),
        TaskFactory(resource=contract.resource),
        TaskFactory(contract=True)
    ]


def test_build_day_existing(contract):
    from krm3.timesheet.operations import DayEntryProcessor

    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day()
    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-02')).build_day()
    with pytest.raises(RuntimeError, match='DayEntry already exists'):
        DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day()
    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day(reset=True)


def test_build_day_reset(contract, tasks):
    from krm3.timesheet.operations import DayEntryProcessor

    day_entry = DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-08')).build_day(
        task_entries=[
            {'task': tasks[0], 'night_shift_hours': 1},
        ],
    ) # Sunday
    assert day_entry.is_holiday is True
    assert day_entry.due_hours == 0
    assert day_entry.meal_voucher == 0
    assert day_entry.remaining_hours == 0

    day_entry = DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-08')).build_day(
        task_entries=[
            {'task': tasks[0], 'night_shift_hours': 1.5},
            {'task': tasks[1], 'day_shift_hours': 1},
        ],
        reset=True,
    )
    assert day_entry.meal_voucher == 1

    from krm3.core.models import TaskEntry
    assert TaskEntry.objects.count() == 2


def test_add_del_task(contract, tasks):
    from krm3.core.models import TaskEntry

    dp = DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-06'))

    day_entry = dp.build_day(
        task_entries=[
            {'task': tasks[0], 'day_shift_hours': 1},
        ],
    )  # Friday

    assert TaskEntry.objects.count() == 1
    assert day_entry.day_hours == 1
    assert day_entry.night_hours == 0
    assert day_entry.meal_voucher == 0

    # Adding the entry
    day_entry = dp.add_task_entry(task=tasks[1], day_shift_hours=2, night_shift_hours=1)

    assert TaskEntry.objects.count() == 2
    assert day_entry.day_hours == 3
    assert day_entry.night_hours == 1
    assert day_entry.meal_voucher == 1

    # Deleting task entry for tasks[0]
    day_entry = dp.del_task_entry(TaskEntry.objects.get(task=tasks[0]).id)
    assert TaskEntry.objects.count() == 1
    assert day_entry.day_hours == 2
    assert day_entry.night_hours == 1
    assert day_entry.meal_voucher == 1
