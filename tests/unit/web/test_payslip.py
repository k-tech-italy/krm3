from django.urls import reverse
from testutils.factories import ResourceFactory, SuperUserFactory

from tests._extras.testutils.factories import TimesheetSubmissionFactory


def test_payslip_report_with_timesheet_submissions(client):
    """Test payslip report includes timesheet submissions in coverage."""
    SuperUserFactory(username='user00', password='pass123')
    resource = ResourceFactory()

    TimesheetSubmissionFactory(resource=resource)

    client.login(username='user00', password='pass123')
    url = reverse('export_report', args=['202001'])
    response = client.get(url)

    assert response.status_code == 200
