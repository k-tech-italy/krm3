from datetime import date

from testutils.factories import DayEntryFactory, ResourceFactory, TimesheetSubmissionFactory


def test_submission_state_is_synchronized_with_day_entries():
    resource = ResourceFactory()
    day_entry = DayEntryFactory(resource=resource, day=date(2024, 1, 3))
    submission = TimesheetSubmissionFactory(
        resource=resource,
        period=('2024-01-01', '2024-01-08'),
        closed=True,
    )

    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is True

    submission.closed = False
    submission.save()
    day_entry.refresh_from_db()
    assert day_entry.timesheet == submission
    assert day_entry.closed is False

    submission.closed = True
    submission.save()
    submission.delete()
    day_entry.refresh_from_db()
    assert day_entry.timesheet is None
    assert day_entry.closed is False
