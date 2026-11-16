from datetime import date
from unittest.mock import Mock

import pytest

from krm3.events import Event
from krm3.events.notifications.holidays import HolidayNotification
from testutils.factories import ResourceFactory


@pytest.mark.django_db
def test_holiday_notification_sends_event_with_sorted_iso_dates(monkeypatch) -> None:
    resource = ResourceFactory(first_name='Ada', last_name='Lovelace', user__email='ada@example.com')
    dates = [date(2024, 1, day) for day in (3, 4, 2)]
    monkeypatch.setattr('krm3.events.notifications.holidays.EventDispatcher.send', send := Mock())

    HolidayNotification()(resource, dates)

    send.assert_called_once_with(
        Event(
            name='holidays',
            payload={
                'resource': {'name': resource.full_name, 'email': resource.user.email},
                'start_date': '2024-01-02',
                'end_date': '2024-01-04',
            },
        )
    )
