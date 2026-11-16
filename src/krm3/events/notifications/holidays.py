import datetime
from collections.abc import Iterable
from typing import override

from krm3.core.models import Resource
from krm3.events import Event
from krm3.events.dispatcher import EventDispatcher
from krm3.events.notifications.base import Notification


class HolidayNotification(Notification):
    """Notify that a resource requested holidays."""

    @override
    def __call__(self, resource: Resource, dates: Iterable[datetime.date]) -> None:
        sorted_dates = sorted(dates)
        EventDispatcher().send(
            Event(
                name='holidays',
                payload={
                    'resource': {'name': resource.full_name, 'email': resource.user.email},
                    'start_date': sorted_dates[0].isoformat(),
                    'end_date': sorted_dates[-1].isoformat(),
                },
            )
        )
