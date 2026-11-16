import pytest
from django.core.management import call_command


def test_lists_available_notifications(capsys: pytest.CaptureFixture[str]) -> None:
    call_command('list_notifications')

    expected = """Available notifications:
- holidays: HolidayNotification
- timesheet_pending: TimesheetPendingNotification
- timesheet_rejected: TimesheetRejectedNotification
- timesheet_approved: TimesheetApprovedNotification
"""
    assert capsys.readouterr().out == expected
