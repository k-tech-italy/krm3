from krm3.events.notifications.holidays import HolidayNotification
from krm3.events.notifications.registry import NOTIFICATIONS
from krm3.events.notifications.timesheets import (
    TimesheetApprovedNotification,
    TimesheetPendingNotification,
    TimesheetRejectedNotification,
)


def test_holiday_notification_is_registered() -> None:
    assert {
        'holidays': HolidayNotification,
        'timesheet_pending': TimesheetPendingNotification,
        'timesheet_rejected': TimesheetRejectedNotification,
        'timesheet_approved': TimesheetApprovedNotification,
    } == NOTIFICATIONS
