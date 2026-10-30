import pytest
from django.core.exceptions import ValidationError

from krm3.core.models import Contract, TaskEntry
from krm3.timesheet.operations import DayEntryProcessor
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, TaskFactory


@pytest.fixture
def contract():
    return ContractFactory(
        working_schedule={'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0},
        meal_voucher={'mon': 2, 'tue': 3, 'wed': 2, 'thu': 2, 'fri': 2, 'sat': 1, 'sun': 2},
        holiday_day=Contract.Weekday.SUNDAY,
    )


@pytest.fixture
def tasks(contract):
    return [
        TaskFactory(resource=contract.resource),
        TaskFactory(resource=contract.resource),
        TaskFactory(contract=True)
    ]


def test_build_day_existing(contract):
    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day()
    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-02')).build_day()
    with pytest.raises(RuntimeError, match='DayEntry already exists'):
        DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day()
    DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-01')).build_day(reset=True)


def test_build_day_reset(contract, tasks):
    day_entry = DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-08')).build_day(
        task_entries=[
            {'task': tasks[0], 'night_shift_hours': 1},
        ],
    ) # Sunday
    assert day_entry.is_holiday is True  # the contract's weekly holiday
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

    assert TaskEntry.objects.count() == 2


def test_add_del_task(contract, tasks):
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


@pytest.mark.parametrize(
    ('day', 'worked_hours', 'bank', 'expected_meal_voucher'),
    [
        ('2023-01-02', 6, -2, 1),
        ('2023-01-03', 0, -8, 1),
        ('2023-01-04', 8, 2, 1),
        ('2023-01-05', 6, 2, 0),
    ],
)
def test_meal_voucher_counts_only_bank_withdrawals(  # noqa: PLR0917
    contract, tasks, day, worked_hours, bank, expected_meal_voucher
):
    contract.working_schedule = {'mon': 8, 'tue': 8, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0}
    contract.meal_voucher = {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8}
    contract.save(update_fields=['working_schedule', 'meal_voucher'])

    day_entry = DayEntryProcessor(resource=contract.resource, day=_dt(day)).build_day(
        task_entries=[{'task': tasks[0], 'day_shift_hours': worked_hours}] if worked_hours else [],
        bank=bank,
    )

    assert day_entry.meal_voucher == expected_meal_voucher


@pytest.mark.parametrize(
    ('bank', 'expected_overtime'),
    (
        pytest.param(0, 2, id='no-bank'),
        pytest.param(1, 1, id='bank-deposit'),
    ),
)
def test_task_hours_above_due_hours_are_overtime(contract, tasks, bank, expected_overtime):
    day_entry = DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-05')).build_day(
        task_entries=[{'task': tasks[0], 'day_shift_hours': 6}],
        bank=bank,
    )  # Thursday, 4 due hours

    assert day_entry.overtime_hours == expected_overtime


@pytest.mark.parametrize(
    'absence',
    (
        pytest.param({'asked_holiday': True}, id='holiday'),
        pytest.param({'is_sick': True}, id='sick'),
    ),
)
def test_rejects_task_hours_on_full_day_absence(contract, tasks, absence):
    with pytest.raises(ValidationError, match='sick day or requested holiday'):
        DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-05')).build_day(
            task_entries=[{'task': tasks[0], 'on_call_hours': 1}],
            **absence,
        )


@pytest.mark.parametrize(
    'absence',
    (
        pytest.param({'leave_hours': 2}, id='leave'),
        pytest.param({'special_leave_hours': 2}, id='special-leave'),
        pytest.param({'rest_hours': 2}, id='rest'),
    ),
)
@pytest.mark.parametrize(
    ('worked_hours', 'accepted'),
    (
        pytest.param(2, True, id='up-to-due-hours'),
        pytest.param(3, False, id='above-due-hours'),
    ),
)
def test_limits_task_hours_to_due_hours_on_partial_absence(contract, tasks, absence, worked_hours, accepted):
    def build_day():
        return DayEntryProcessor(resource=contract.resource, day=_dt('2023-01-05')).build_day(
            task_entries=[{'task': tasks[0], 'day_shift_hours': worked_hours}],
            **absence,
        )  # Thursday, 4 due hours

    if accepted:
        assert build_day().overtime_hours == 0
    else:
        with pytest.raises(ValidationError, match='cannot exceed the due hours'):
            build_day()
