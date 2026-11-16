from krm3.events.notifications.base import Notification
from krm3.events.notifications.holidays import HolidayNotification
from krm3.events.notifications.timesheets import (
    TimesheetApprovedNotification,
    TimesheetPendingNotification,
    TimesheetRejectedNotification,
)

NOTIFICATIONS: dict[str, type[Notification]] = {
    'holidays': HolidayNotification,
    'timesheet_pending': TimesheetPendingNotification,
    'timesheet_rejected': TimesheetRejectedNotification,
    'timesheet_approved': TimesheetApprovedNotification,
}
