import datetime
import typing
from datetime import date
import json
from unittest.mock import patch

import pytest
from constance.test import override_config
from django.core.exceptions import ValidationError
from django.core.files import File
from django.urls import reverse
from psycopg.types.range import DateRange

from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    ExtraHolidayFactory,
    ProjectFactory,
    ResourceFactory,
    SuperUserFactory,
    TaskFactory,
    UserFactory,
)
from testutils.permissions import add_permissions

from krm3.core.forms import ContractForm
from krm3.core.models import Contract, DayEntry, TaskEntry
from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from _pytest.raises import RaisesExc


@pytest.fixture
def contract_2023():
    return ContractFactory(period=(_dt('2023-01-01'), None))


def test_contract_upper_bond_must_be_one_day_greater():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 1)
    with pytest.raises(ValidationError, match='End date must be at least one day after start date.'):
        ContractFactory(period=(start_dt, end_dt))


def test_create_contract_with_correct_period():
    start_dt = date(2020, 1, 1)
    end_dt = date(2020, 1, 2)
    ContractFactory(period=(start_dt, end_dt))


@pytest.mark.parametrize(
    'period, day, expected',
    [
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-02'), True),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-01'), False),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-01-31'), True),
        ((_dt('2020-01-02'), _dt('2020-02-01')), _dt('2020-02-01'), False),
        ((_dt('2020-01-02'), None), _dt('2020-01-02'), True),
        ((_dt('2020-01-02'), None), _dt('2020-01-01'), False),
    ],
)
def test_falls_in(period: tuple, day: datetime.date | KrmDay, expected: bool):
    contract = ContractFactory(period=period)
    assert contract.falls_in(day) is expected


def test_contract_ordering():
    c1 = ContractFactory(period=(_dt('20250601'), _dt('20250630')))
    c2 = ContractFactory(period=(_dt('20250503'), _dt('20250601')))
    assert list(Contract.objects.values_list('id', flat=True)) == [c2.id, c1.id]


# @pytest.mark.parametrize(
#     'cnum, new_lower, new_upper, valid',
#     [
#         pytest.param(0, _dt('20200401'), None, True, id='c1-start-ok'),
#         pytest.param(0, _dt('20200402'), None, False, id='c1-start-short'),
#         pytest.param(3, None, _dt('20200316'), True, id='c4-end-ok'),
#         pytest.param(3, None, _dt('20200315'), False, id='c4-end-short'),
#         pytest.param(1, _dt('20200702'), None, False, id='c2-start-short'),
#         pytest.param(2, None, _dt('22000101'), False, id='c3-end-short'),
#     ],
# )
# def test_amend_contract_with_tasks(cnum, new_lower, new_upper, valid, contracts_and_tasks):
#     contract = contracts_and_tasks['contracts'][cnum]
#
#     lower = contract.period.lower.strftime('%Y-%m-%d')
#     upper = contract.period.upper.strftime('%Y-%m-%d') if contract.period.upper else ''
#
#     if new_lower:
#         lower = new_lower
#     elif new_upper:
#         upper = new_upper
#
#     data = {'resource': contract.resource, 'period_0': lower, 'period_1': upper}
#     form = ContractForm(instance=contract, data=data)
#
#     assert form.is_valid() is valid, form.errors
#
#
# @pytest.mark.parametrize(
#     'cnum, expected',
#     [
#         pytest.param(0, [0, 1], id='c1'),
#         pytest.param(1, [1, 2], id='c2'),
#         pytest.param(2, [2], id='c3'),
#         pytest.param(3, [3], id='c4'),
#         pytest.param(4, [], id='c5'),
#     ],
# )
# def test_get_tasks(cnum, expected, contracts_and_tasks):
#     contract = contracts_and_tasks['contracts'][cnum]
#     assert contract.get_tasks() == [contracts_and_tasks['tasks'][x] for x in expected]


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7})
)
def test_get_due_hours_regular_week():
    with_schedule = ContractFactory(
        period=(_dt('2024-01-01'), None),
        working_schedule={'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6},
    )
    without_schedule = ContractFactory(period=(_dt('2024-01-01'), None))
    for x in range(7):
        day = KrmDay('2024-05-06') + x  # 6th is a Monday
        actual = with_schedule.get_due_hours(day)
        expected = x if x < 6 else 0
        assert (
            actual == expected
        ), f'Unexpected value ({actual} != {expected}, with_schedule) for {day} {day.day_of_week_short}'
        actual = without_schedule.get_due_hours(day)
        expected = (x + 1) if x < 6 else 0
        assert (
            actual == expected
        ), f'Unexpected value ({actual} != {expected}, without_schedule) for {day} {day.day_of_week_short}'


def test_get_due_hours_sundays():
    contract = ContractFactory(
        period=(_dt('2023-01-01'), None),
        working_schedule={'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6},
    )
    no_sun_hol = ContractFactory(
        period=(_dt('2023-01-01'), None),
        working_schedule={'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6},
        sunday_as_holiday=False,
    )
    assert contract.is_holiday(_dt('2023-01-01')) is True
    assert contract.get_due_hours(_dt('2023-01-01')) == 0
    assert no_sun_hol.is_holiday(_dt('2023-01-01')) is True
    assert no_sun_hol.get_due_hours(_dt('2023-01-01')) == 0

    assert contract.is_holiday(_dt('2023-01-08')) is True
    assert contract.get_due_hours(_dt('2023-01-08')) == 0
    assert no_sun_hol.is_holiday(_dt('2023-01-08')) is False
    assert no_sun_hol.get_due_hours(_dt('2023-01-08')) == 6


@pytest.mark.parametrize(
    'day, expected_fixed, expected_unbounded',
    (
        pytest.param(
            _dt('20230111'),
            pytest.raises(RuntimeError, match='Unable to get due hours: date outside contract period'),
            pytest.raises(RuntimeError, match='Unable to get due hours: date outside contract period'),
            id='before_contract',
        ),
        pytest.param(_dt('2024-01-02'), 4, 4, id='during_contract'),
        pytest.param(_dt('2025-01-31'), 4, 4, id='last_day_in_contract'),
        pytest.param(
            _dt('2025-02-01'),
            pytest.raises(RuntimeError, match='Unable to get due hours: date outside contract period'),
            1,
            id='end_of_fixed_contract',
        ),
    ),
)
def test_get_due_hours_boundaries(
    day,
    expected_fixed: 'RaisesExc[RuntimeError] | int',
    expected_unbounded: 'RaisesExc[RuntimeError] | int',
):
    fixed_period = (_dt('2024-01-01'), _dt('2025-02-01'))
    unbounded_period = (_dt('2024-01-01'), None)
    schedule = {'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 1, 'sun': 0}

    fixed_time_contract = ContractFactory(period=fixed_period, working_schedule=schedule)
    unbounded_contract = ContractFactory(period=unbounded_period, working_schedule=schedule)

    if isinstance(expected_fixed, int):
        assert fixed_time_contract.get_due_hours(day) == expected_fixed
    else:
        with expected_fixed:
            fixed_time_contract.get_due_hours(day)
    if isinstance(expected_unbounded, int):
        assert unbounded_contract.get_due_hours(day) == expected_unbounded
    else:
        with expected_unbounded:
            unbounded_contract.get_due_hours(day)

#
# def test_document_url_returns_none_when_no_file(db):
#     contract = ContractFactory()
#     assert contract.document_url is None
#
#
# def test_document_url_returns_authenticated_url_when_file_exists(db):
#     document = MagicMock(spec=File)
#     document.name = 'contract.pdf'
#     contract = ContractFactory(document=document)
#
#     expected_url = reverse('media-auth:contract-document', args=[contract.pk])
#     assert contract.document_url == expected_url
#
#
# def test_accessible_by_superuser_can_access_all_contracts(db):
#     """Superuser should have access to all contracts."""
#     superuser = SuperUserFactory()
#     contract1 = ContractFactory()
#     contract2 = ContractFactory()
#
#     result = Contract.objects.accessible_by(superuser)
#
#     assert contract1 in result
#     assert contract2 in result
#
#
# def test_accessible_by_user_with_view_any_contract_permission(db):
#     """User with view_any_contract permission should access all contracts."""
#     user = UserFactory()
#     ResourceFactory(user=user)
#     add_permissions(user, 'core.view_any_contract')
#     contract1 = ContractFactory()
#     contract2 = ContractFactory()
#
#     result = Contract.objects.accessible_by(user)
#
#     assert contract1 in result
#     assert contract2 in result
#
#
# def test_accessible_by_user_with_manage_any_contract_permission(db):
#     """User with manage_any_contract permission should access all contracts."""
#     user = UserFactory()
#     ResourceFactory(user=user)
#     add_permissions(user, 'core.manage_any_contract')
#     contract1 = ContractFactory()
#     contract2 = ContractFactory()
#
#     result = Contract.objects.accessible_by(user)
#
#     assert contract1 in result
#     assert contract2 in result
#
#
# def test_accessible_by_user_with_matching_resource(db):
#     """User can access contracts belonging to their resource."""
#     user = UserFactory()
#     resource = ResourceFactory(user=user)
#     own_contract = ContractFactory(resource=resource)
#     other_contract = ContractFactory()  # Different resource
#
#     result = Contract.objects.accessible_by(user)
#
#     assert own_contract in result
#     assert other_contract not in result
#
#
# def test_accessible_by_user_without_resource_returns_empty(db):
#     """User without an associated resource should get empty queryset."""
#     user = UserFactory()
#     # User has no resource associated
#     contract = ContractFactory()
#
#     result = Contract.objects.accessible_by(user)
#
#     assert result.count() == 0
#     assert contract not in result
#
#
# def test_accessible_by_get_resource_exception_returns_empty(db, monkeypatch):
#     """When get_resource() raises an exception, should return empty queryset."""
#     user = UserFactory()
#     contract = ContractFactory()
#
#     def raise_exception():
#         raise RuntimeError('Database error')
#
#     monkeypatch.setattr(user, 'get_resource', raise_exception)
#
#     result = Contract.objects.accessible_by(user)
#
#     assert result.count() == 0
#     assert contract not in result
#
#


@pytest.mark.parametrize(
    'sunday_as_holiday, day, expected',
    [
        pytest.param(True, _dt('2023-01-08'), True, id='sun_holiday-sunday'),
        pytest.param(False, _dt('2023-01-08'), False, id='no_sun_holiday-sunday'),
        pytest.param(True, _dt('2023-01-06'), True, id='sun_holiday-epiphany'),
        pytest.param(False, _dt('2023-01-06'), True, id='no_sun_holiday-epiphany'),
        pytest.param(True, _dt('2023-01-10'), False, id='sun_holiday-tuesday'),
        pytest.param(False, _dt('2023-01-10'), False, id='no_sun_holiday-tuesday'),
        pytest.param(False, _dt('2023-01-01'), True, id='new-year-sunday'),
    ],
)
def test_contract_is_holiday(sunday_as_holiday, day, expected):
    contract = ContractFactory(sunday_as_holiday=sunday_as_holiday)
    assert contract.is_holiday(day) is expected


@pytest.mark.parametrize(
    'day, expected',
    [
        pytest.param(_dt('2023-01-04'), True, id='Wednesday'),
        pytest.param(_dt('2023-01-05'), False, id='Thursday'),
        pytest.param(_dt('2023-01-06'), True, id='epiphany'),
        pytest.param(_dt('2023-01-08'), False, id='Sunday'),
    ],
)
def test_contract_is_holiday_with_extra_holiday(day, expected):
    ExtraHolidayFactory(
        period=(_dt('2023-01-02'), _dt('2023-01-05')),
        country_codes=['IT-RM'],
        reason='Extra holiday test',
    )
    contract = ContractFactory(sunday_as_holiday=False)
    assert contract.is_holiday(day) is expected


@pytest.mark.parametrize(
    'schedule, expected',
    [
        pytest.param('aaa', 'aaa', id='provided'),
        pytest.param({}, {'mon': 5, 'tue': 6, 'wed': 7, 'thu': 8, 'fri': 2, 'sat': 3, 'sun': 1}, id='default'),
    ]
)
def test_work_schedule(schedule, expected):
    with override_config(
            DEFAULT_RESOURCE_SCHEDULE='{"mon": 5, "tue": 6, "wed": 7, "thu": 8, "fri": 2, "sat": 3, "sun": 1}'):
        c = ContractFactory(working_schedule=schedule)
        assert c.work_schedule == expected


@pytest.mark.parametrize(
    'period, expected',
    [
        pytest.param(
            (_dt('20260101'), _dt('20260501')),
            (_dt('20260101'), _dt('20260501')),
            id='regular'
        ),
        pytest.param(
            (_dt('20260101'), None),
            (_dt('20260101'), _dt('99991231')),
            id='unbounded'
        ),
    ]
)
def test_period_as_tuple(period: DateRange, expected):
    c = Contract(period=DateRange(*period))
    assert c.period_as_tuple() == expected


@pytest.mark.parametrize(
    'period, expected',
    [
        pytest.param(
            (_dt('20260101'), _dt('20260501')),
            '2026-01-01 - 2026-04-30',
            id='regular'
        ),
        pytest.param(
            (_dt('20260101'), None),
            '2026-01-01 - ...',
            id='unbounded'
        ),
    ]
)
def test_contract_str(period: tuple[str, str | None], expected):
    c = ContractFactory(period=DateRange(*period))
    assert str(c) == f'{c.resource}, {expected}'


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7})
)
def test_is_working_day():
    contract = ContractFactory(period=(_dt('20231201'), _dt('20231231')))
    assert (
            contract.is_working_day(_dt('20231224')),
            contract.is_working_day(_dt('20231225')),
            contract.is_working_day(_dt('20231226')),
            contract.is_working_day(_dt('20231227')),
           ) == (False, False, False, True)


def test_meal_voucher(contract_2023):
    # if no meal_voucher is set it returns None regardless of the attribute
    assert contract_2023.meal_threshold(day=None) is None

    contract_2023.meal_voucher={'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7}

    assert [contract_2023.meal_threshold(KrmDay('2023-09-04') + x) for x in range(7)] == list(range(1, 8))


def test_build_day_calls_refresh(contract_2023):
    day = _dt('2023-01-10')
    with patch("krm3.core.models.timesheets.DayEntry.refresh", side_effect=DayEntry.refresh, autospec=True) as mock:
        day_entry = contract_2023.build_day(day)

    assert len(entries := list(DayEntry.objects.filter(pk=day_entry.id))) == 1
    assert entries[0].day == day
    assert mock.call_count == 1



def test_validate_rule_with_overtime_and_meal_voucher(contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][0]

    tasks = [TaskFactory(resource=contract.resource,
                         period=(contract.period.lower, contract.period.upper),
                         ) for x in range(2)]
    day = _dt('2020-01-07')  # Tuesday

    # Set schedule to 4 hours for this day
    contract.working_schedule = {'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0}
    contract.meal_voucher = {'tue': 2.0}  # 2 hours threshold
    contract.save()

    from krm3.core.models import Task
    # 1. Work 4 hours (exactly due hours)
    day_entry = contract.build_day(
        day,
        task_entries=[
            {'task_id': tasks[0].pk, 'day_shift_hours': 4},
        ],
    )
    assert day_entry.due_hours == 4
    assert day_entry.regular_hours == 4
    assert day_entry.worked_hours == 4
    assert day_entry.overtime_hours == 0
    assert day_entry.remaining_hours == 0
    assert day_entry.meal_voucher == 1

    # Overriding same task updates
    day_entry.taskentry_set.update(day_shift_hours=1.5)
    day_entry.refresh(task_entries=None, drop_existing=False)
    assert day_entry.due_hours == 4
    assert day_entry.regular_hours == 1.5
    assert day_entry.worked_hours == 1.5
    assert day_entry.overtime_hours == 0
    assert day_entry.remaining_hours == 2.5
    assert day_entry.meal_voucher == 0

    # 2. Add another task: work 5.5 hours (overtime)
    day_entry = day_entry.add_task_entry(task=tasks[1], day_shift_hours=1.5, night_shift_hours=2.5, travel_hours=1)
    assert day_entry.regular_hours == 4  # Capped at due_hours
    assert day_entry.worked_hours == 6.5
    assert day_entry.overtime_hours == 2.5
    assert day_entry.remaining_hours == 0
    assert day_entry.meal_voucher == 1

    # 2. Del other task
    day_entry = day_entry.del_task_entry(task_or_entry=tasks[0])
    assert day_entry.regular_hours == 4  # Capped at due_hours
    assert day_entry.worked_hours == 5
    assert day_entry.overtime_hours == 1
    assert day_entry.remaining_hours == 0
    assert day_entry.meal_voucher == 1


#
#
# def test_build_day_with_task_object():
#     contract = contract_2023
#     task = TaskFactory(resource=contract.resource)
#     day = _dt('2023-01-10')
#
#     day_entry = contract.build_day(
#         day,
#         task_entries=[
#             {'task': task, 'date': day, 'day_shift_hours': 4},
#         ],
#     )
#
#     assert day_entry.taskentry_set.count() == 1
#     assert day_entry.taskentry_set.first().task == task
#
#
# def test_build_day_passes_kwargs_to_day_entry():
#     contract = contract_2023
#     day_entry = contract.build_day(_dt('2023-01-10'), comment='test note')
#
#     assert day_entry.comment == 'test note'
#
#
# @override_config(
#     DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0})
# )
# def test_build_day_idempotent():
#     contract = contract_2023
#     task = TaskFactory(resource=contract.resource)
#     day = _dt('2023-01-10')
#
#     first = contract.build_day(day, task_entries=[{'task_id': task.pk, 'date': day, 'day_shift_hours': 6}])
#     assert first.taskentry_set.count() == 1
#
#     # Second call should reuse the same DayEntry and reset task entries
#     second = contract.build_day(day, comment='updated')
#     assert second.pk == first.pk
#     assert second.taskentry_set.count() == 0
#     assert second.comment == 'updated'
#
#
# def test_build_day_raises_without_task_id_or_task():
#     contract = contract_2023
#     day = _dt('2023-01-10')
#
#     with pytest.raises(ValueError, match='Either task_id or task must be provided'):
#         contract.build_day(day, task_entries=[{'date': day, 'day_shift_hours': 4}])

'/'
