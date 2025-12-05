import datetime
import json

import pytest
from bs4 import BeautifulSoup
from constance.test import override_config
from django.urls import reverse
from freezegun import freeze_time
from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    ProjectFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    SuperUserFactory,
    TaskFactory,
    TimeEntryFactory,
)

from tests.unit.web.test_views import _assert_homepage_content


@override_config(
    DEFAULT_RESOURCE_SCHEDULE=json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 8, 'sun': 8})
)
@freeze_time('2025-08-22')
def test_availability_view_current_month(client):
    SuperUserFactory(username='user00', password='pass123')
    resource = ResourceFactory()
    ContractFactory(resource=resource)
    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        date=datetime.date.today(),
        holiday_hours=8,
    )
    TimeEntryFactory(
        resource=resource,
        date=datetime.date.today() + datetime.timedelta(days=1),
        day_shift_hours=0,
        leave_hours=3,
        special_leave_hours=3,
        special_leave_reason=SpecialLeaveReasonFactory(),
    )
    client.login(username='user00', password='pass123')
    url = reverse('availability')
    response = client.get(url)
    _assert_homepage_content(response)
    assert response.status_code == 200

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Assert title
    assert '<h1 class="title">Availability Report August 2025</h1>' in response.content.decode()

    # Find the report table
    table = soup.find('table', class_='report-table')
    assert table is not None, 'Report table not found'

    # Find all data rows (skip header row)
    tbody = table.find('tbody')
    assert tbody is not None, 'Table body not found'
    data_rows = tbody.find_all('tr', class_='row-data')
    assert len(data_rows) > 0, 'No data rows found in table'

    # Find the row for the resource (first cell should contain resource name)
    resource_row = None
    for row in data_rows:
        row_header = row.find('td', class_='row-header')
        if row_header and f'{resource.first_name} {resource.last_name}' in row_header.get_text():
            resource_row = row
            break

    assert resource_row is not None, f'Row for resource {resource.first_name} {resource.last_name} not found'

    # Get all cell data from the resource row
    cell_data = [cell.get_text().strip() for cell in resource_row.find_all('td', class_='cell-data')]

    # Assert that 'H' (holiday) appears in at least one cell
    assert 'H' in cell_data, 'Holiday indicator "H" not found in resource row cells'

    # Assert that 'L 3.00, SL 3.00' (leave and special leave) appears in at least one cell
    assert 'L 3.00, SL 3.00' in cell_data, 'Leave indicator "L 3.00, SL 3.00" not found in resource row cells'


@freeze_time('2025-10-17')
def test_availability_view_filtered_by_project(client):
    SuperUserFactory(username='user00', password='pass123')
    project = ProjectFactory()
    resource = ResourceFactory()
    ContractFactory(resource=resource)
    TaskFactory(project=project, resource=resource)
    another_project = ProjectFactory()
    another_resource = ResourceFactory()
    ContractFactory(resource=another_resource)
    TaskFactory(project=another_project, resource=another_resource)
    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        date=_dt('20251017'),
        holiday_hours=8,
    )
    TimeEntryFactory(
        resource=another_resource,
        day_shift_hours=0,
        date=_dt('20251017'),
        leave_hours=3,
    )
    client.login(username='user00', password='pass123')
    url = reverse('availability')
    response = client.get(f'{url}?project={project.id}')
    _assert_homepage_content(response)
    assert response.status_code == 200
    content = response.content.decode()
    assert f'{resource.first_name} {resource.last_name}' in content
    assert f'{another_resource.first_name} {another_resource.last_name}' not in content
    assert 'H' in content
    assert 'L 3.00' not in content


@freeze_time('2025-08-22')
def test_availability_report_only_resources_with_contract(client):
    """Test that unprivileged user gets their own resource when project filter excludes them."""
    project = ProjectFactory()

    r_current = ResourceFactory()
    ContractFactory(resource=r_current)
    r_past = ResourceFactory()
    ContractFactory(resource=r_past, period=(_dt('2020-01-01'), _dt('2021-01-01')))
    r_future = ResourceFactory()
    ContractFactory(resource=r_future, period=(_dt('2025-09-01'), _dt('2026-01-01')))

    TaskFactory(project=project, resource=r_current)
    TaskFactory(project=project, resource=r_past, end_date=_dt('20201231'))
    TaskFactory(project=project, resource=r_future)

    client.login(username=r_current.user.username, password=r_current.user._password)

    url = reverse('availability')
    response = client.get(f'{url}?project={project.id}')

    assert response.status_code == 200
    content = response.content.decode()

    assert f'{r_current.first_name} {r_current.last_name}' in content
    assert f'{r_past.first_name} {r_past.last_name}' not in content
    assert f'{r_future.first_name} {r_future.last_name}' not in content


@freeze_time('2025-08-22')
@pytest.mark.parametrize(
    'month, expected_result',
    [
        pytest.param('202509', 'Availability Report September 2025', id='next_month'),
        pytest.param('202507', 'Availability Report July 2025', id='previous_month'),
    ],
)
def test_availability_view_next_previous_month(client, month, expected_result):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(reverse('availability-report-month', args=[month]))
    _assert_homepage_content(response)
    assert response.status_code == 200
    assert f'<h1 class="title">{expected_result}</h1>' in response.content.decode()
