import datetime
import io
import json
from unittest.mock import patch, mock_open

import openpyxl
import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission

from krm3.timesheet.report import timeentry_key_mapping

from testutils.factories import (
    ProjectFactory,
    UserFactory,
    SuperUserFactory,
    ResourceFactory,
    TimeEntryFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
)
from urllib.parse import urlencode

from freezegun import freeze_time


def _assert_homepage_content(response):
    assert response.status_code == 200
    content = response.content.decode()

    report_expected_url = reverse('report')
    task_report_expected_url = reverse('task_report')
    availability_report_expected_url = reverse('availability')
    releases_expected_url = reverse('releases')

    assert 'Report' in content
    assert 'Report by task' in content
    assert 'Availability report' in content
    assert f'href="{report_expected_url}"' in content
    assert f'href="{task_report_expected_url}"' in content
    assert f'href="{availability_report_expected_url}"' in content
    assert f'href="{releases_expected_url}"' in content


@pytest.mark.parametrize('url', ('/be/', '/be/home/', '/be/availability/'))
def test_authenticated_user_should_see_homepage_and_availability_report(client, url):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(url)
    _assert_homepage_content(response)


@pytest.mark.parametrize('url', ('/be/report/', '/be/task_report/', '/be/releases/'))
def test_superuser_should_see_permission_protected_views(client, url):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(url)
    _assert_homepage_content(response)


@pytest.mark.parametrize('url', ('/be/report/', '/be/task_report/', '/be/releases/'))
def test_user_without_permissions_should_not_see_permission_protected_views(
    url, client
):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.parametrize('url', ('/be/report/', '/be/task_report/', '/be/releases/'))
def test_user_with_permissions_should_see_permission_protected_views(url, client):
    for perm in ['manage_any_timesheet', 'view_any_timesheet']:
        user = UserFactory(username='user00', password='pass123')
        user.user_permissions.add(Permission.objects.get(codename=perm))
        client.login(username='user00', password='pass123')
        response = client.get(url)
        _assert_homepage_content(response)


@pytest.mark.parametrize(
    'url', ('/be/home/', '/be/', '/be/availability/', '/be/report/', '/be/task_report/', '/be/releases/')
)
def test_not_authenticated_user_should_be_redirected_to_login_page(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f'/admin/login/?next={url}'


@freeze_time('2025-08-22')
def test_availability_view_current_month(client):
    SuperUserFactory(username='user00', password='pass123')
    resource = ResourceFactory()
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
    content = response.content.decode()
    assert (
        f'<td class="border border-1 text-left p-1 ">{resource.first_name} {resource.last_name}</td>'
        in content
    )
    assert '<td class="p-1 border border-1 text-center">H</td>' in content
    assert '<td class="p-1 border border-1 text-center">L 6.00</td>' in content
    assert (
        '<h1 class="text-3xl font-bold text-center mb-1">Availability August 2025</h1>'
        in content
    )


def test_availability_view_filtered_by_project(client):
    SuperUserFactory(username='user00', password='pass123')
    project = ProjectFactory()
    resource = ResourceFactory()
    TaskFactory(project=project, resource=resource)
    another_project = ProjectFactory()
    another_resource = ResourceFactory()
    TaskFactory(project=another_project, resource=another_resource)
    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        date=datetime.date.today(),
        holiday_hours=8,
    )
    TimeEntryFactory(
        resource=another_resource,
        day_shift_hours=0,
        date=datetime.date.today(),
        leave_hours=3,
    )
    client.login(username='user00', password='pass123')
    url = reverse('availability')
    response = client.get(f'{url}?project={project.id}')
    _assert_homepage_content(response)
    assert response.status_code == 200
    content = response.content.decode()
    assert (
        f'<td class="border border-1 text-left p-1 ">{resource.first_name} {resource.last_name}</td>'
        in content
    )
    assert (
        f'<td class="border border-1 text-left p-1 ">{another_resource.first_name} {another_resource.last_name}</td>'
        not in content
    )
    assert '<td class="p-1 border border-1 text-center">H</td>' in content
    assert '<td class="p-1 border border-1 text-center">L 3.00</td>' not in content


@freeze_time('2025-08-22')
@pytest.mark.parametrize(
    'month, expected_result',
    [
        pytest.param('202509', 'Availability September 2025', id='next_month'),
        pytest.param('202507', 'Availability July 2025', id='previous_month'),
    ],
)
def test_availability_view_next_previous_month(client, month, expected_result):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(f'{reverse('availability')}?{urlencode({"month": month})}')
    _assert_homepage_content(response)
    assert response.status_code == 200
    assert (
        f'<h1 class="text-3xl font-bold text-center mb-1">{expected_result}</h1>'
        in response.content.decode()
    )


@freeze_time('2025-08-22')
def test_report_view_current_month(client):
    SuperUserFactory(username='user00', password='pass123')
    resource = ResourceFactory()
    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        date=datetime.date.today(),
        holiday_hours=8,
    )
    client.login(username='user00', password='pass123')
    url = reverse('report')
    response = client.get(url)
    _assert_homepage_content(response)
    assert response.status_code == 200
    content = response.content.decode()
    assert f'{resource.first_name} {resource.last_name}' in content
    assert '<td class="p-1 border border-1 text-center">8</td>' in content
    assert (
        '<h1 class="text-3xl font-bold text-center mb-1">Report August 2025</h1>'
        in content
    )


@freeze_time('2025-08-22')
@pytest.mark.parametrize(
    'month, expected_result',
    [
        pytest.param('202509', 'Report September 2025', id='next_month'),
        pytest.param('202507', 'Report July 2025', id='previous_month'),
    ],
)
def test_report_view_next_previous_month(client, month, expected_result):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(f'{reverse('report')}?{urlencode({"month": month})}')
    _assert_homepage_content(response)
    assert response.status_code == 200
    assert (
        f'<h1 class="text-3xl font-bold text-center mb-1">{expected_result}</h1>'
        in response.content.decode()
    )


@freeze_time('2025-08-22')
def test_task_report_view_current_month(client):
    SuperUserFactory(username='user00', password='pass123')
    task = TaskFactory()
    TimeEntryFactory(
        resource=task.resource, day_shift_hours=8, date=datetime.date.today(), task=task
    )
    client.login(username='user00', password='pass123')
    url = reverse('task_report')
    response = client.get(url)
    _assert_homepage_content(response)
    assert response.status_code == 200
    content = response.content.decode()
    assert (
        f'<td class="border border-1 text-left p-1 ">{task.project}: {task.title}</td>'
        in content
    )
    assert (
        '<h1 class="text-3xl font-bold text-center mb-1">Task Report August 2025</h1>'
        in content
    )


@freeze_time('2025-08-22')
@pytest.mark.parametrize(
    'month, expected_result',
    [
        pytest.param('202509', 'Task Report September 2025', id='next_month'),
        pytest.param('202507', 'Task Report July 2025', id='previous_month'),
    ],
)
def test_task_report_view_next_previous_month(client, month, expected_result):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(f'{reverse('task_report')}?{urlencode({"month": month})}')
    _assert_homepage_content(response)
    assert response.status_code == 200
    assert (
        f'<h1 class="text-3xl font-bold text-center mb-1">{expected_result}</h1>'
        in response.content.decode()
    )

@pytest.mark.django_db
def test_report_creation(client):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    task_1 = TaskFactory()
    task_2 = TaskFactory()

    TimeEntryFactory(
        date=datetime.date(2025, 6, 10),
        day_shift_hours=8,
        task=task_1,
        resource=task_1.resource,
    )
    TimeEntryFactory(
        date=datetime.date(2025, 6, 12),
        day_shift_hours=6,
        task=task_1,
        resource=task_1.resource,
    )

    TimeEntryFactory(
        date=datetime.date(2025, 6, 13),
        night_shift_hours=7,
        task=task_1,
        resource=task_2.resource,
    )

    url = reverse('export_report', args=['202506'])
    response = client.get(url)
    assert response.status_code == 200
    assert (
        response['Content-Type']
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    workbook = openpyxl.load_workbook(filename=io.BytesIO(response.content))

    # check sheet names
    r1_name = f'{task_1.resource.last_name.upper()} {task_1.resource.first_name}'
    r2_name = f'{task_2.resource.last_name.upper()} {task_2.resource.first_name}'
    assert r1_name, r2_name in workbook.sheetnames
    sheet_1 = workbook[r1_name]
    sheet_2 = workbook[r2_name]

    # check row labels
    assert sheet_1['A1'].value == r1_name
    assert sheet_1['A2'].value == 'Giorni'
    row_labels = [sheet_1[f'A{index}'].value for index in range(3, 12)]
    assert all(value in timeentry_key_mapping.values() for value in row_labels)

    # check day labels
    assert sheet_1['C2'].value == '**Sun\n1**'
    assert sheet_1['AF2'].value == '**Mon\n30**'
    assert sheet_1['AG2'].value is None

    # check cell values
    assert sheet_1['L3'].value == 8
    assert sheet_1['Q3'].value is None
    assert sheet_2['O4'].value == 7

    # check total hours
    assert sheet_1['B3'].value == 14
    assert sheet_2['B4'].value == 7

@pytest.mark.django_db
def test_unauthorized_report_creation(client):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    url = reverse('export_report', args=['202506'])
    response = client.get(url)
    assert response.status_code == 403

@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
    "v1.0.0": {
        "features": ["Login support", "Dashboard refresh"],
        "fixes": ["Memory leak", "404 on tasks"],
        "release_notes": ["Initial production deployment"]
    }
}))
@patch('os.path.join', return_value='/fake/path/releases.json')
def test_releases_view_with_valid_json(mock_join, mock_file, client):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    response = client.get(reverse('releases'))
    content = response.content.decode()

    assert response.status_code == 200
    assert "v1.0.0" in content
    assert "Login support" in content
    assert "Memory leak" in content
    assert "Initial production deployment" in content

def test_releases_view_with_missing_file_should_show_no_releases(client):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    with patch('os.path.join', return_value='/nonexistent/path/releases.json'):
        response = client.get(reverse('releases'))
        content = response.content.decode()

        assert response.status_code == 200
        assert "No releases found" in content

@patch('builtins.open', new_callable=mock_open, read_data='{invalid json}')
@patch('os.path.join', return_value='/fake/path/releases.json')
def test_releases_view_with_invalid_json_should_show_no_releases(mock_join, mock_file, client):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    with patch('builtins.open', mock_open(read_data="{ invalid json }")):
        with patch('os.path.join', return_value='/fake/path/releases.json'):
            response = client.get(reverse('releases'))
            content = response.content.decode()

            assert response.status_code == 200
            assert "No releases found" in content
