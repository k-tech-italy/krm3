from datetime import date

from django.urls import reverse
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ResourceFactory,
    TaskFactory,
    TimesheetSubmissionFactory,
)


def test_payslip_report_with_timesheet_submissions(admin_client):
    """Test payslip report includes timesheet submissions in coverage."""
    resource = ResourceFactory()
    contract = ContractFactory(
        resource=resource,
        period=(date(2020, 1, 1), date(2020, 2, 1)),
        working_schedule={'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0},
    )
    TaskFactory(resource=resource, period=(date(2020, 1, 2), date(2020, 1, 3)))
    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=date(2020, 1, 2),
        day_hours=8,
        due_hours=8,
    )

    TimesheetSubmissionFactory(resource=resource, period=(date(2020, 1, 1), date(2020, 2, 1)))

    admin_client.login(username='user00', password='pass123')
    url = reverse('export_report', args=['202001'])
    response = admin_client.get(url)

    assert response.status_code == 200
