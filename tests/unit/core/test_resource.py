import datetime
import json
import typing
from datetime import date

import pytest
from constance.test import override_config
from django.test import override_settings
from ktcalendars import KTDateRange, KTDay
from ktcalendars.utils import dt
from testutils.factories import ContractFactory, ResourceFactory

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract, Resource


@pytest.fixture
def contracts_list() -> list['Contract']:
    c1: Contract = ContractFactory(period=(date(2020, 1, 1), date(2020, 7, 1)))
    c2: Contract = ContractFactory(resource=c1.resource, period=(date(2020, 9, 1), date(2021, 1, 1)))
    c3: Contract = ContractFactory(resource=c1.resource, period=(date(2021, 1, 1), None))
    c4: Contract = ContractFactory(period=(date(2021, 1, 1), None))
    return [c1, c2, c3, c4]


@pytest.mark.parametrize(
    'contracts, country_code, expected',
    [
        pytest.param([[dt('20230620'), dt('20230625')], [dt('20230701'), None]], 'IT-RM', [0] * 6, id='outside'),
        pytest.param(
            [[dt('20230620'), dt('20230626')], [dt('20230629'), None]], 'IT-RM', [7, 0, 0, 0, 0, 5], id='edges'
        ),
        pytest.param(
            [[dt('20230627'), dt('20230630')]], 'IT', [0, 0, 2, 3, 4, 0], id='inside'
        ),
    ],
)
def test_get_schedule_returns_zero_if_there_is_no_contract(contracts, country_code, expected):
    resource = ResourceFactory()
    for period in contracts:
        ContractFactory(
            resource=resource,
            period=period,
            country_calendar_code=country_code,
            working_schedule={'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7},
        )
    start_day, end_day = dt('20230625'), dt('20230630')
    schedule = resource.get_schedule(start_day, end_day)

    assert schedule == {
        d: expected[i] for i, d in enumerate(KTDateRange.from_start_end(start_day, end_day))
    }


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7})
)
@pytest.mark.parametrize(
    'start_day, end_day, country_calendar_code, custom_schedule, expected_schedule',
    [
        (
            dt('20200101'),
            dt('20200103'),
            'IT-RM',
            {},
            {
                KTDay('2020-01-01'): 0,  # New Year
                KTDay('2020-01-02'): 4,
                KTDay('2020-01-03'): 5,
            },
        ),
        (
            dt('20201110'),
            dt('20201112'),
            'IT-RM',
            {},
            {KTDay('2020-11-10'): 2, KTDay('2020-11-11'): 3, KTDay('2020-11-12'): 4},
        ),
        (
            date(2020, 11, 10),
            date(2020, 11, 15),
            'PL',
            {},
            {
                KTDay('2020-11-10'): 2,
                KTDay('2020-11-11'): 0,  # polish Independence Day
                KTDay('2020-11-12'): 4,
                KTDay('2020-11-13'): 5,
                KTDay('2020-11-14'): 6,
                KTDay('2020-11-15'): 7,
            },
        ),
        (
            dt('20201110'),
            dt('20201115'),
            'PL',
            {'mon': 2, 'tue': 3, 'wed': 4, 'thu': 5, 'fri': 6, 'sat': 7, 'sun': 8},
            {
                KTDay('2020-11-10'): 3,
                KTDay('2020-11-11'): 0,  # polish Independence Day
                KTDay('2020-11-12'): 5,
                KTDay('2020-11-13'): 6,
                KTDay('2020-11-14'): 7,
                KTDay('2020-11-15'): 8,
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
