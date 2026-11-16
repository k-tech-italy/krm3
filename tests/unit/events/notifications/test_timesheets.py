from datetime import date
from unittest.mock import Mock

import pytest
from psycopg.types.range import DateRange
from testutils.factories import TimesheetSubmissionFactory

from krm3.events import Event
from krm3.events.notifications.timesheets import (
    TimesheetApprovedNotification,
    TimesheetPendingNotification,
    TimesheetRejectedNotification,
)


@pytest.mark.django_db
def test_timesheet_pending_notification_sends_event(monkeypatch) -> None:
    submission = TimesheetSubmissionFactory(
        period=DateRange(date(2024, 1, 1), date(2024, 2, 1), '[)'),
    )
    monkeypatch.setattr('krm3.events.notifications.timesheets.EventDispatcher.send', send := Mock())

    TimesheetPendingNotification()(submission)

    send.assert_called_once_with(
        Event(
            name='timesheet_pending',
            payload={
                'submission_id': submission.pk,
                'resource': {'name': submission.resource.full_name, 'email': submission.resource.user.email},
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
            },
        )
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('notification', 'name', 'extra'),
    [
        pytest.param(TimesheetApprovedNotification, 'timesheet_approved', {}, id='approved'),
        pytest.param(
            TimesheetRejectedNotification,
            'timesheet_rejected',
            {'rejection_message': 'Please correct the bank hours.'},
            id='rejected',
        ),
    ],
)
def test_timesheet_review_notifications_send_events(monkeypatch, notification, name, extra) -> None:
    submission = TimesheetSubmissionFactory(rejection_message=extra.get('rejection_message', ''))
    monkeypatch.setattr('krm3.events.notifications.timesheets.EventDispatcher.send', send := Mock())

    notification()(submission)

    send.assert_called_once_with(
        Event(
            name=name,
            payload={
                'submission_id': submission.pk,
                'resource': {'name': submission.resource.full_name, 'email': submission.resource.user.email},
                'start_date': submission.period.lower.isoformat(),
                'end_date': (submission.period.upper - date.resolution).isoformat(),
                **extra,
            },
        )
    )
