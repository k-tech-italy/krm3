import datetime
import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission

from testutils.factories import (
    UserFactory,
    SuperUserFactory,
    ResourceFactory,
    TimeEntryFactory,
    SpecialLeaveReasonFactory,
    TaskFactory
)
from urllib.parse import urlencode

from freezegun import freeze_time



def _assert_homepage_content(response):
    assert response.status_code == 200
    content = response.content.decode()

    report_expected_url = reverse('report')
    task_report_expected_url = reverse('task_report')
    availability_report_expected_url = reverse('availability')

    assert 'Report' in content
    assert 'Report by task' in content
    assert 'Availability report' in content
    assert f'href="{report_expected_url}"' in content
    assert f'href="{task_report_expected_url}"' in content
    assert f'href="{availability_report_expected_url}"' in content


@pytest.mark.parametrize(
    'permissions',
    (
        ['manage_any_timesheet', 'view_any_timesheet'],
        ['manage_any_timesheet'],
        ['view_any_timesheet'],
    ),
)
def test_authenticated_user_with_permissions_should_see_homepage(permissions, client):
    user = UserFactory(username='user00', password='pass123')
    for perm in permissions:
        user.user_permissions.add(Permission.objects.get(codename=perm))
    client.login(username='user00', password='pass123')

    url = reverse("home")
    response = client.get(url)
    _assert_homepage_content(response)


def test_superuser_should_see_homepage(client):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    url = reverse("home")
    response = client.get(url)
    _assert_homepage_content(response)


@pytest.mark.parametrize('url', ('/be/home/', '/be/', '/be/availability/', '/be/report/', '/be/task_report/'))
def test_user_without_permissions_should_not_see_web_urls(url, client):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.parametrize('url', ('/be/home/', '/be/', '/be/availability/', '/be/report/', '/be/task_report/'))
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
    assert (
        f'{resource.first_name} {resource.last_name}'
        in content
    )
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
        resource=task.resource,
        day_shift_hours=8,
        date=datetime.date.today(),
        task=task
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
