import datetime
import json
import typing
from datetime import date
from ktcalendars.utils import dt
from unittest.mock import patch

import pytest
from constance.test import override_config
from django.core.exceptions import ValidationError
from django.urls import reverse
from ktcalendars import KTDay
from psycopg.types.range import DateRange
from testutils.factories import (
    ContractFactory,
    ResourceFactory,
    TaskFactory,
    UserFactory,
)
from testutils.permissions import add_permissions

from krm3.core.models import Contract, DayEntry
from contextlib import nullcontext as does_not_raise

if typing.TYPE_CHECKING:
    from _pytest.raises import RaisesExc


err_date_outside_contract = pytest.raises(ValueError, match='Date outside contract period')


@pytest.fixture
def contract_2023():
    return ContractFactory(period=(dt('2023-01-01'), None))


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
        ((dt('2020-01-02'), dt('2020-02-01')), dt('2020-01-02'), True),
        ((dt('2020-01-02'), dt('2020-02-01')), dt('2020-01-01'), False),
        ((dt('2020-01-02'), dt('2020-02-01')), dt('2020-01-31'), True),
        ((dt('2020-01-02'), dt('2020-02-01')), dt('2020-02-01'), False),
        ((dt('2020-01-02'), None), dt('2020-01-02'), True),
        ((dt('2020-01-02'), None), dt('2020-01-01'), False),
    ],
)
def test_falls_in(period: tuple, day: datetime.date | KTDay, expected: bool):
    contract = ContractFactory(period=period)
    assert (contract.get_ktday(day, silent=True) is not None) is expected


def test_contract_ordering():
    c1 = ContractFactory(period=(dt('20250601'), dt('20250630')))
    c2 = ContractFactory(period=(dt('20250503'), dt('20250601')))
    assert list(Contract.objects.values_list('id', flat=True)) == [c2.id, c1.id]


# @pytest.mark.parametrize(
#     'cnum, new_lower, new_upper, valid',
#     [
#         pytest.param(0, dt('20200401'), None, True, id='c1-start-ok'),
#         pytest.param(0, dt('20200402'), None, False, id='c1-start-short'),
#         pytest.param(3, None, dt('20200316'), True, id='c4-end-ok'),
#         pytest.param(3, None, dt('20200315'), False, id='c4-end-short'),
#         pytest.param(1, dt('20200702'), None, False, id='c2-start-short'),
#         pytest.param(2, None, dt('22000101'), False, id='c3-end-short'),
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
@pytest.mark.parametrize(
    'daynum, expected',
    [
        pytest.param(0, (0, 0), id='mon'),
        pytest.param(1, (1, 1), id='tue'),
        pytest.param(2, (2, 2), id='wed'),
        pytest.param(3, (3, 3), id='thu'),
        pytest.param(4, (4, 4), id='fri'),
        pytest.param(5, (5, 0), id='sat'),
        pytest.param(6, (6, 0), id='sun'),
    ],
)
@pytest.mark.parametrize('with_schedule', [[True], [False]])
def test_get_due_hours_regular_week(daynum: int, expected: tuple[int, int], with_schedule: bool):
    contract = ContractFactory(
        period=(dt('2024-01-01'), None),
        working_schedule={'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        if with_schedule
        else None,
    )
    actual = contract.get_due_hours(KTDay('2024-05-06') + daynum)
    assert actual == expected[0 if with_schedule else 1]


def test_get_due_hours_holidays():
    base = {
        'period': (dt('2023-01-01'), None),
        'working_schedule': {'mon': 4, 'tue': 2, 'wed': 2, 'thu': 2, 'fri': 2, 'sat': 2, 'sun': 2},
    }
    ita = ContractFactory(country_calendar_code='IT', **base)
    rome = ContractFactory(country_calendar_code='IT-RM', **base)
    assert ita.get_ktday('2026-06-29').is_holiday is False
    assert ita.get_due_hours('2026-06-29') == 4
    assert rome.get_ktday(dt('2026-06-29')).is_holiday is True
    assert rome.get_due_hours(dt('2026-06-29')) == 0


@pytest.mark.parametrize(
    'day, expectation, expected_value, period',
    [
        pytest.param('2023-01-31', err_date_outside_contract, None, 'bound', id="before-bound"),
        pytest.param('2023-02-01', does_not_raise(), 3, 'bound', id="lower-bound"),
        pytest.param('2023-02-28', does_not_raise(), 2, 'bound', id="upper-bound"),
        pytest.param('2023-03-01', err_date_outside_contract, None, 'bound', id="after-bound"),
        pytest.param('2023-01-31', err_date_outside_contract, None, 'unbounded', id="before-unbounded"),
        pytest.param('2023-02-01', does_not_raise(), 3, 'unbounded', id="lower-unbounded"),
        pytest.param('2023-02-28', does_not_raise(), 2, 'unbounded', id="upper-unbounded"),
        pytest.param('2023-03-01', does_not_raise(), 3, 'unbounded', id="after-unbounded"),
    ],
)
def test_get_due_hours_boundaries(
        day: str,
        expectation: 'RaisesExc[ValueError]',
        expected_value: int | None,
        period: str
):
    contract_period = (dt('2023-02-01'), dt('2023-03-01') if period == 'bound' else None)
    contract = ContractFactory(
        period=contract_period, working_schedule={'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 0}
    )

    with expectation:
        value = contract.get_due_hours(day)
        assert value == expected_value


def test_document_url_returns_none_when_no_file(db):
    contract = ContractFactory()
    assert contract.document_url is None


def test_document_url_returns_authenticated_url_when_file_exists(db):
    contract = ContractFactory()
    contract.document = 'contracts/documents/R1/C1/contract.pdf'

    expected_url = reverse('media-auth:contract-document', args=[contract.pk])
    assert contract.document_url == expected_url


def test_accessible_by_superuser_can_access_all_contracts(admin_user):
    """Superuser should have access to all contracts."""
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.filter_acl(admin_user)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_view_any_contract_permission(db):
    """User with view_any_contract permission should access all contracts."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.view_any_contract')
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.filter_acl(user)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_manage_any_contract_permission(db):
    """User with manage_any_contract permission should access all contracts."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.manage_any_contract')
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.filter_acl(user)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_matching_resource(db):
    """User can access contracts belonging to their resource."""
    user = UserFactory()
    resource = ResourceFactory(user=user)
    own_contract = ContractFactory(resource=resource)
    other_contract = ContractFactory()  # Different resource

    result = Contract.objects.filter_acl(user)

    assert own_contract in result
    assert other_contract not in result


def test_accessible_by_user_without_resource_returns_empty(db):
    """User without an associated resource should get empty queryset."""
    user = UserFactory()
    # User has no resource associated
    contract = ContractFactory()

    result = Contract.objects.filter_acl(user)

    assert result.count() == 0
    assert contract not in result


def test_accessible_by_get_resource_exception_returns_empty(db, monkeypatch):
    """When get_resource() raises an exception, should return empty queryset."""
    user = UserFactory()
    contract = ContractFactory()

    def raise_exception():
        raise RuntimeError('Database error')

    monkeypatch.setattr(user, 'get_resource', raise_exception)

    result = Contract.objects.filter_acl(user)

    assert result.count() == 0
    assert contract not in result


@pytest.mark.parametrize(
    'schedule, expected',
    [
        pytest.param('aaa', 'aaa', id='provided'),
        pytest.param({}, {'mon': 5, 'tue': 6, 'wed': 7, 'thu': 8, 'fri': 2, 'sat': 3, 'sun': 1}, id='default'),
    ],
)
def test_work_schedule(schedule, expected):
    with override_config(
        DEFAULT_RESOURCE_SCHEDULE='{"mon": 5, "tue": 6, "wed": 7, "thu": 8, "fri": 2, "sat": 3, "sun": 1}'
    ):
        c = ContractFactory(working_schedule=schedule)
        assert c.work_schedule == expected


@pytest.mark.parametrize(
    'period, expected',
    [
        pytest.param((dt('20260101'), dt('20260501')), '2026-01-01 - 2026-04-30', id='regular'),
        pytest.param((dt('20260101'), None), '2026-01-01 - ...', id='unbounded'),
    ],
)
def test_contract_str(period: tuple[str, str | None], expected):
    c = ContractFactory(period=DateRange(*period))
    assert str(c) == f'{c.resource}, {expected}'


def test_meal_voucher(contract_2023):
    # if no meal_voucher is set it returns None regardless of the attribute
    assert contract_2023.meal_threshold(day=None) is None

    contract_2023.meal_voucher = {'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7}

    assert [contract_2023.meal_threshold(KTDay('2023-09-04') + x) for x in range(7)] == list(range(1, 8))


@pytest.mark.parametrize(
    'period, day, expected',
    [
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-15'), True, id='inside_contract'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-01'), True, id='first_day'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-30'), True, id='last_day'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2022-12-31'), False, id='before_contract'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-02-01'), False, id='after_contract'),
        pytest.param((dt('2023-01-01'), None), dt('2023-06-15'), True, id='unbounded_inside'),
        pytest.param((dt('2023-01-01'), None), dt('2022-12-31'), False, id='unbounded_before'),
    ],
)
def test_get_ktday_silent_true(period, day, expected):
    contract = ContractFactory(period=period)
    result = contract.get_ktday(day, silent=True)
    if expected:
        assert result is not None
        assert result.date == day
        assert result.ktcalendar.country_calendar_code == contract.calendar_code
    else:
        assert result is None


@pytest.mark.parametrize(
    'period, day, should_raise',
    [
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-15'), False, id='inside_contract'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-01'), False, id='first_day'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-01-30'), False, id='last_day'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2022-12-31'), True, id='before_contract'),
        pytest.param((dt('2023-01-01'), dt('2023-01-31')), dt('2023-02-01'), True, id='after_contract'),
        pytest.param((dt('2023-01-01'), None), dt('2023-06-15'), False, id='unbounded_inside'),
        pytest.param((dt('2023-01-01'), None), dt('2022-12-31'), True, id='unbounded_before'),
    ],
)
def test_get_ktday_silent_false(period, day, should_raise):
    contract = ContractFactory(period=period)
    if should_raise:
        with pytest.raises(ValueError, match='Date outside contract period'):
            contract.get_ktday(day, silent=False)
    else:
        result = contract.get_ktday(day, silent=False)
        assert result is not None
        assert result.date == day
        assert result.ktcalendar.country_calendar_code == contract.calendar_code


def test_get_ktday_with_ktday_input(contract_2023):
    ktday = KTDay('2023-06-15', cal_country_code='IT')
    result = contract_2023.get_ktday(ktday, silent=True)
    assert result is not None
    assert result.date == ktday.date
    assert result.ktcalendar.country_calendar_code == contract_2023.calendar_code


def test_build_day_calls_refresh(contract_2023):
    day = dt('2023-01-10')
    with patch('krm3.core.models.timesheets.DayEntry.refresh', side_effect=DayEntry.refresh, autospec=True) as mock:
        day_entry = contract_2023.build_day(day)

    assert len(entries := list(DayEntry.objects.filter(pk=day_entry.id))) == 1
    assert entries[0].day == day
    assert mock.call_count == 1


def test_validate_rule_with_overtime_and_meal_voucher(contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][0]

    tasks = [
        TaskFactory(
            resource=contract.resource,
            period=(contract.period.lower, contract.period.upper),
        )
        for x in range(2)
    ]
    day = dt('2020-01-07')  # Tuesday

    # Set schedule to 4 hours for this day
    contract.working_schedule = {'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0}
    contract.meal_voucher = {'tue': 2.0}  # 2 hours threshold
    contract.save()

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


@pytest.mark.parametrize(
    'start_date, end_date, expected',
    [
        (dt('20260101'), dt('20260115'), [0, 1]),
        (dt('20260101'), dt('20260114'), [0]),
        (dt('20240101'), dt('20240115'), []),
        (dt('20260101'), dt('20260302'), [0, 1, 2]),
        (dt('20270101'), dt('20270302'), [1]),
    ],
)
def test_active_between(start_date, end_date, expected):
    contracts = [
        c1 := ContractFactory(period=(dt('20260101'), dt('20260201'))),
        c2 := ContractFactory(period=(dt('20260115'), None)),
        c3 := ContractFactory(period=(dt('20260301'), dt('20260501')), resource=c1.resource)
    ]

    assert list(Contract.objects.active_between(start_date, end_date).values_list('id', flat=True)) == [
        contracts[i].id for i in expected
    ] 