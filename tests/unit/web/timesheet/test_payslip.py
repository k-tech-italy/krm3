from django.urls import reverse
from testutils.factories import ResourceFactory

from testutils.factories import TimesheetSubmissionFactory


def test_payslip_report_with_timesheet_submissions(admin_client):
    """Test payslip report includes timesheet submissions in coverage."""
    resource = ResourceFactory()

    TimesheetSubmissionFactory(resource=resource)

    admin_client.login(username='user00', password='pass123')
    url = reverse('export_report', args=['202001'])
    response = admin_client.get(url)

    assert response.status_code == 200
