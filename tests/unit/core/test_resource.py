import datetime
import json
from datetime import date
import pytest
from constance.test import override_config
from django.test import override_settings

from testutils.factories import ResourceFactory, ContractFactory


@override_config(DEFAULT_RESOURCE_SCHEDULE=json.dumps({
    'mon': 1,
    'tue': 2,
    'wed': 3,
    'thu': 4,
    'fri': 5,
    'sat': 6,
    'sun': 7
}))
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
        datetime.date(2020, 1, 10): 5
    }


@override_config(DEFAULT_RESOURCE_SCHEDULE=json.dumps({
    'mon': 1,
    'tue': 2,
    'wed': 3,
    'thu': 4,
    'fri': 5,
    'sat': 6,
    'sun': 7
}))
@pytest.mark.parametrize(
    'start_day, end_day, country_calendar_code, custom_schedule, expected_schedule', [
        (
            date(2020, 1, 1),
            date(2020, 1, 3),
            'IT-RM',
            None,
            {
                datetime.date(2020, 1, 1): 0, # New Year
                datetime.date(2020, 1, 2): 4,
                datetime.date(2020, 1, 3): 5
            }
        ),
        (
            date(2020, 11, 10),
            date(2020, 11, 12),
            'IT-RM',
            None,
            {
                datetime.date(2020, 11, 10): 2,
                datetime.date(2020, 11, 11): 3,
                datetime.date(2020, 11, 12): 4
            }
        ),
        (
                date(2020, 11, 10),
                date(2020, 11, 15),
                'PL',
                None,
                {
                    datetime.date(2020, 11, 10): 2,
                    datetime.date(2020, 11, 11): 0, # polish Independence Day
                    datetime.date(2020, 11, 12): 4,
                    datetime.date(2020, 11, 13): 5,
                    datetime.date(2020, 11, 14): 6,
                    datetime.date(2020, 11, 15): 7,
                }
        ),
        (
                date(2020, 11, 10),
                date(2020, 11, 15),
                'PL',
                {
                    'mon': 2,
                    'tue': 3,
                    'wed': 4,
                    'thu': 5,
                    'fri': 6,
                    'sat': 7,
                    'sun': 8
                },
                {
                    datetime.date(2020, 11, 10): 3,
                    datetime.date(2020, 11, 11): 0,  # polish Independence Day
                    datetime.date(2020, 11, 12): 5,
                    datetime.date(2020, 11, 13): 6,
                    datetime.date(2020, 11, 14): 7,
                    datetime.date(2020, 11, 15): 8,
                }
        ),

    ]
)
def test_get_schedule_with_contract(start_day, end_day, country_calendar_code, custom_schedule, expected_schedule):
    contract = ContractFactory(country_calendar_code=country_calendar_code,
                               period=(start_day, end_day + datetime.timedelta(days=1)),
                               working_schedule=custom_schedule)
    schedule = contract.resource.get_schedule(start_day, end_day)

    assert schedule == expected_schedule
