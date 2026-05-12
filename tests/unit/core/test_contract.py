import datetime
import typing
from datetime import date
import json
from unittest.mock import MagicMock

import pytest
from constance import test as constance_test
from django.core.exceptions import ValidationError
from django.core.files import File
from django.urls import reverse
from psycopg.types.range import DateRange

from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    ProjectFactory,
    ResourceFactory,
    SuperUserFactory,
    TaskFactory,
    UserFactory,
)
from testutils.permissions import add_permissions

from krm3.core.forms import ContractForm
from krm3.core.models import Contract
from krm3.utils.dates import KrmDay


if typing.TYPE_CHECKING:
    from _pytest.raises import RaisesExc


@pytest.fixture
def contracts_and_tasks():
    project = ProjectFactory(start_date=datetime.date(2019, 1, 1), end_date=None)

    c1: Contract = ContractFactory(period=(_dt('2020-01-01'), _dt('2020-07-01')))
    c2: Contract = ContractFactory(resource=c1.resource, period=(_dt('2020-07-01'), _dt('2021-01-01')))
    c3: Contract = ContractFactory(resource=c1.resource, period=(_dt('2021-01-01'), None))
    c4: Contract = ContractFactory(period=(_dt('2019-01-01'), _dt('2020-05-01')))
    c5: Contract = ContractFactory(resource=c4.resource, period=(_dt('2020-05-01'), _dt('2020-10-01')))

    return {
        'contracts': [c1, c2, c3, c4, c5],
        'tasks': [
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 4, 1),
                end_date=datetime.date(2020, 6, 15),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 6, 1),
                end_date=datetime.date(2020, 8, 31),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                start_date=datetime.date(2020, 8, 1),
                end_date=None,
            ),
            TaskFactory(
                resource=c4.resource,
                project=project,
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 3, 15),
            ),
        ],
    }


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


@pytest.mark.parametrize(
    'cnum, new_lower, new_upper, valid',
    [
        pytest.param(0, _dt('20200401'), None, True, id='c1-start-ok'),
        pytest.param(0, _dt('20200402'), None, False, id='c1-start-short'),
        pytest.param(3, None, _dt('20200316'), True, id='c4-end-ok'),
        pytest.param(3, None, _dt('20200315'), False, id='c4-end-short'),
        pytest.param(1, _dt('20200702'), None, False, id='c2-start-short'),
        pytest.param(2, None, _dt('22000101'), False, id='c3-end-short'),
    ],
)
def test_amend_contract_with_tasks(cnum, new_lower, new_upper, valid, contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][cnum]

    lower = contract.period.lower.strftime('%Y-%m-%d')
    upper = contract.period.upper.strftime('%Y-%m-%d') if contract.period.upper else ''

    if new_lower:
        lower = new_lower
    elif new_upper:
        upper = new_upper

    data = {'resource': contract.resource, 'period_0': lower, 'period_1': upper}
    form = ContractForm(instance=contract, data=data)

    assert form.is_valid() is valid, form.errors


@pytest.mark.parametrize(
    'cnum, expected',
    [
        pytest.param(0, [0, 1], id='c1'),
        pytest.param(1, [1, 2], id='c2'),
        pytest.param(2, [2], id='c3'),
        pytest.param(3, [3], id='c4'),
        pytest.param(4, [], id='c5'),
    ],
)
def test_get_tasks(cnum, expected, contracts_and_tasks):
    contract = contracts_and_tasks['contracts'][cnum]
    assert contract.get_tasks() == [contracts_and_tasks['tasks'][x] for x in expected]


@constance_test.override_config(
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


def test_document_url_returns_none_when_no_file(db):
    contract = ContractFactory()
    assert contract.document_url is None


def test_document_url_returns_authenticated_url_when_file_exists(db):
    document = MagicMock(spec=File)
    document.name = 'contract.pdf'
    contract = ContractFactory(document=document)

    expected_url = reverse('media-auth:contract-document', args=[contract.pk])
    assert contract.document_url == expected_url


def test_accessible_by_superuser_can_access_all_contracts(db):
    """Superuser should have access to all contracts."""
    superuser = SuperUserFactory()
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.accessible_by(superuser)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_view_any_contract_permission(db):
    """User with view_any_contract permission should access all contracts."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.view_any_contract')
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.accessible_by(user)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_manage_any_contract_permission(db):
    """User with manage_any_contract permission should access all contracts."""
    user = UserFactory()
    ResourceFactory(user=user)
    add_permissions(user, 'core.manage_any_contract')
    contract1 = ContractFactory()
    contract2 = ContractFactory()

    result = Contract.objects.accessible_by(user)

    assert contract1 in result
    assert contract2 in result


def test_accessible_by_user_with_matching_resource(db):
    """User can access contracts belonging to their resource."""
    user = UserFactory()
    resource = ResourceFactory(user=user)
    own_contract = ContractFactory(resource=resource)
    other_contract = ContractFactory()  # Different resource

    result = Contract.objects.accessible_by(user)

    assert own_contract in result
    assert other_contract not in result


def test_accessible_by_user_without_resource_returns_empty(db):
    """User without an associated resource should get empty queryset."""
    user = UserFactory()
    # User has no resource associated
    contract = ContractFactory()

    result = Contract.objects.accessible_by(user)

    assert result.count() == 0
    assert contract not in result


def test_accessible_by_get_resource_exception_returns_empty(db, monkeypatch):
    """When get_resource() raises an exception, should return empty queryset."""
    user = UserFactory()
    contract = ContractFactory()

    def raise_exception():
        raise RuntimeError('Database error')

    monkeypatch.setattr(user, 'get_resource', raise_exception)

    result = Contract.objects.accessible_by(user)

    assert result.count() == 0
    assert contract not in result


@pytest.mark.parametrize(
    'period, expected',
    [
        pytest.param(DateRange(_dt('20260101'), _dt('20260501')), (_dt('20260101'), _dt('20260501')), id='regular'),
        pytest.param(DateRange(_dt('20260101'), None), (_dt('20260101'), _dt('99991231')), id='unbounded'),
    ],
)
def test_period_as_tuple(period: DateRange, expected):
    c = Contract(period=period)
    assert c.period_as_tuple() == expected
