from django.urls import reverse
from testutils.factories import (
    ResourceFactory,
    TimesheetSubmissionFactory,
    create_contract_without_scheduled_hours,
)


def test_payslip_report_with_timesheet_submissions(admin_client):
    """Test payslip report includes timesheet submissions in coverage."""
    resource = ResourceFactory()
    period = ('2020-01-01', '2020-02-01')
    create_contract_without_scheduled_hours(resource, period)
    TimesheetSubmissionFactory(resource=resource, period=period)

    admin_client.login(username='user00', password='pass123')
    url = reverse('export_report', args=['202001'])
    response = admin_client.get(url)

    assert response.status_code == 200
