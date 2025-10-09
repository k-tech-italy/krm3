import datetime
import json
import typing
from datetime import date
import pytest
from constance.test import override_config
from django.test import override_settings


from krm3.utils.dates import KrmDay
from testutils.date_utils import _dt
from testutils.factories import ResourceFactory, ContractFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Resource, Contract


@pytest.fixture
def contracts_list() -> list['Contract']:
    c1: Contract = ContractFactory(period=(date(2020, 1, 1), date(2020, 7, 1)))
    c2: Contract = ContractFactory(resource=c1.resource, period=(date(2020, 9, 1), date(2021, 1, 1)))
    c3: Contract = ContractFactory(resource=c1.resource, period=(date(2021, 1, 1), None))
    c4: Contract = ContractFactory(period=(date(2021, 1, 1), None))
    return [c1, c2, c3, c4]


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7})
)
@override_settings(HOLIDAYS_CALENDAR='IT-RM')
def test_get_schedule_returns_default_if_there_is_no_contract():
    resource = ResourceFactory()
    start_day = date(2020, 1, 1)
    end_day = date(2020, 1, 10)
    schedule = resource.get_schedule(start_day, end_day)

    assert schedule == {
        datetime.date(2020, 1, 1): 0,
        datetime.date(2020, 1, 2): 4,
        datetime.date(2020, 1, 3): 5,
        datetime.date(2020, 1, 4): 6,
        datetime.date(2020, 1, 5): 7,
        datetime.date(2020, 1, 6): 0,
        datetime.date(2020, 1, 7): 2,
        datetime.date(2020, 1, 8): 3,
        datetime.date(2020, 1, 9): 4,
        datetime.date(2020, 1, 10): 5,
    }


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7})
)
@pytest.mark.parametrize(
    'start_day, end_day, country_calendar_code, custom_schedule, expected_schedule',
    [
        (
            date(2020, 1, 1),
            date(2020, 1, 3),
            'IT-RM',
            {},
            {
                datetime.date(2020, 1, 1): 0,  # New Year
                datetime.date(2020, 1, 2): 4,
                datetime.date(2020, 1, 3): 5,
            },
        ),
        (
            date(2020, 11, 10),
            date(2020, 11, 12),
            'IT-RM',
            {},
            {datetime.date(2020, 11, 10): 2, datetime.date(2020, 11, 11): 3, datetime.date(2020, 11, 12): 4},
        ),
        (
            date(2020, 11, 10),
            date(2020, 11, 15),
            'PL',
            {},
            {
                datetime.date(2020, 11, 10): 2,
                datetime.date(2020, 11, 11): 0,  # polish Independence Day
                datetime.date(2020, 11, 12): 4,
                datetime.date(2020, 11, 13): 5,
                datetime.date(2020, 11, 14): 6,
                datetime.date(2020, 11, 15): 7,
            },
        ),
        (
            date(2020, 11, 10),
            date(2020, 11, 15),
            'PL',
            {'mon': 2, 'tue': 3, 'wed': 4, 'thu': 5, 'fri': 6, 'sat': 7, 'sun': 8},
            {
                datetime.date(2020, 11, 10): 3,
                datetime.date(2020, 11, 11): 0,  # polish Independence Day
                datetime.date(2020, 11, 12): 5,
                datetime.date(2020, 11, 13): 6,
                datetime.date(2020, 11, 14): 7,
                datetime.date(2020, 11, 15): 8,
            },
        ),
    ],
)
def test_get_schedule_with_contract(start_day, end_day, country_calendar_code, custom_schedule, expected_schedule):
    contract = ContractFactory(
        country_calendar_code=country_calendar_code,
        period=(start_day, end_day + datetime.timedelta(days=1)),
        working_schedule=custom_schedule,
    )
    schedule = contract.resource.get_schedule(start_day, end_day)

    assert schedule == expected_schedule


@pytest.mark.parametrize(
    'contracts, expected',
    [
        pytest.param([['20230601', None]], [1, 1, 1, 1, 1, 1, 1], id='open-ended'),
        pytest.param([['20230628', '20230630']], [0, 0, 0, 0, 1, 1, 0], id='from-28'),
        pytest.param([['20230601', '20230628']], [1, 1, 1, 1, 0, 0, 0], id='until-27'),
    ],
)
def test_get_krm_days_with_contract_days(contracts, expected):
    resource: 'Resource' = ResourceFactory()
    contract_generated = [None]
    for contract_from, contract_to in contracts:
        contract_generated.append(
            ContractFactory(resource=resource, period=(_dt(contract_from), _dt(contract_to) if contract_to else None))
        )
    result = resource.get_krm_days_with_contract(_dt('20230624'), _dt('20230630'))
    assert result == [
        KrmDay('2023-06-24'),
        KrmDay('2023-06-25'),
        KrmDay('2023-06-26'),
        KrmDay('2023-06-27'),
        KrmDay('2023-06-28'),
        KrmDay('2023-06-29'),
        KrmDay('2023-06-30'),
    ]
    assert [kd.contract for kd in result] == [contract_generated[x] for x in expected]


@pytest.mark.parametrize(
    'country_code, expected',
    [
        pytest.param(None, True, id='default'),
        pytest.param('IT-RM', True, id='IT-RM'),
        pytest.param('IT-MI', False, id='IT-MI'),
    ],
)
def test_get_krm_days_with_contract_holidays(country_code, expected):
    contract: 'Contract' = ContractFactory(
        period=(_dt('20230601'), _dt('20230630')), country_calendar_code=country_code
    )
    result = contract.resource.get_krm_days_with_contract(_dt('20230624'), _dt('20230630'))

    assert [d.is_holiday() for d in result] == [False, True, False, False, False, expected, False]


@pytest.mark.parametrize(
    'schedule, expected',
    [
        pytest.param({}, [0, 0, 8, 8, 8, 0, 0], id='default'),
        pytest.param(
            {'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}, [0, 0, 8, 8, 8, 0, 0], id='full'
        ),
        pytest.param(
            {'mon': 4, 'tue': 2, 'wed': 3, 'thu': 5, 'fri': 1, 'sat': 0, 'sun': 0}, [0, 0, 4, 2, 3, 0, 0], id='partial'
        ),
        pytest.param(
            {'mon': 8, 'tue': 8, 'wed': 0, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
            [0, 0, 8, 8, 0, 0, 0],
            id='no-wednesday',
        ),
    ],
)
def test_get_krm_days_with_contract_min_working_hours(schedule, expected):
    # NB: Contract from 1st Jun to 29th Jun. Hence 30th 0 hours
    contract: 'Contract' = ContractFactory(period=(_dt('20230601'), _dt('20230630')), working_schedule=schedule)
    result = contract.resource.get_krm_days_with_contract(_dt('20230624'), _dt('20230630'))
    assert [kd.min_working_hours for kd in result] == expected


@pytest.mark.parametrize(
    'start_date, end_date, expected',
    [
        pytest.param(_dt('20190101'), _dt('20191231'), [], id='before'),
        pytest.param(_dt('20250101'), None, [2], id='after'),
        pytest.param(_dt('20190101'), _dt('20200101'), [0], id='first'),
        pytest.param(_dt('20200701'), None, [1, 2], id='open'),
        pytest.param(_dt('20200701'), _dt('20200831'), [], id='between-contracts'),
        pytest.param(_dt('20200630'), _dt('20200901'), [0, 1], id='just-across'),
        pytest.param(_dt('20200901'), _dt('20200901'), [1], id='fisrt-day'),
        pytest.param(_dt('20200630'), _dt('20200630'), [0], id='last-day'),
    ],
)
def test_get_contracts(start_date, end_date, expected, contracts_list):
    resource: 'Resource' = contracts_list[0].resource
    contracts = resource.get_contracts(start_date, end_date)
    assert contracts == [contracts_list[x] for x in expected]
