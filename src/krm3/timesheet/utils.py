import datetime

from dateutil.relativedelta import relativedelta

from krm3.core.models import Resource, User, TimesheetSubmission
from krm3.timesheet.api.serializers import TimesheetSerializer
from krm3.timesheet.dto import TimesheetDTO


def get_resource_timesheet(
    end_date: datetime.date, resource: 'Resource', start_date: datetime.date, requestor: 'User'
) -> dict:
    """Retrieve the resource timesheet for a specific date interval."""
    tms = TimesheetSubmission.objects.filter(
        resource=resource, period=[start_date, end_date + relativedelta(days=1)]
    ).first()

    if tms and tms.closed and tms.timesheet:
        return tms.timesheet

    timesheet = TimesheetDTO(requested_by=requestor).fetch(resource, start_date, end_date)
    return TimesheetSerializer(timesheet).data
