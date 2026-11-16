import datetime as dt
from typing import override

from krm3.core.models import TimesheetSubmission
from krm3.events import Event
from krm3.events.dispatcher import EventDispatcher
from krm3.events.notifications.base import Notification


class TimesheetNotification(Notification):
    event_name: str

    def _payload(self, submission: TimesheetSubmission) -> dict[str, object]:
        return {
            'submission_id': submission.pk,
            'resource': {'name': submission.resource.full_name, 'email': submission.resource.user.email},
            'start_date': submission.period.lower.isoformat(),
            'end_date': (submission.period.upper - dt.timedelta(days=1)).isoformat(),
        }

    @override
    def __call__(self, submission: TimesheetSubmission, **extra: str) -> None:
        EventDispatcher().send(Event(name=self.event_name, payload={**self._payload(submission), **extra}))


class TimesheetPendingNotification(TimesheetNotification):
    event_name = 'timesheet_pending'


class TimesheetRejectedNotification(TimesheetNotification):
    event_name = 'timesheet_rejected'

    def __call__(self, submission: TimesheetSubmission, **extra: str) -> None:
        super().__call__(submission, rejection_message=submission.rejection_message, **extra)


class TimesheetApprovedNotification(TimesheetNotification):
    event_name = 'timesheet_approved'
