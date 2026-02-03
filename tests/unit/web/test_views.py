import datetime

import freezegun
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from testutils.factories import (
    ContractFactory,
    ResourceFactory,
    UserFactory,
    WorkScheduleFactory,
    MealVoucherThresholdsFactory,
)


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


@pytest.mark.parametrize(
    'url', ('/be/', '/be/home/', '/be/availability/', '/be/releases/', '/be/report/', '/be/task_report/')
)
def test_resource_user_can_see_all_report_links(resource_client, url):
    response = resource_client.get(url)
    _assert_homepage_content(response)


@pytest.mark.parametrize(
    'url',
    [
        pytest.param('/be/report/', id='report'),
        pytest.param('/be/task_report/', id='task_report'),
    ],
)
def test_user_without_permission_can_only_see_their_reports(url, resource_client):
    another_user = UserFactory(username='user01', password='pass123')
    another_resource = ResourceFactory(user=another_user, profile=another_user.profile)
    response = resource_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    resource_name = f'{resource_client._resource.last_name}</strong> {resource_client._resource.first_name}'
    another_user_name = f'{another_resource.last_name}</strong> {another_resource.first_name}'
    assert resource_name in content, f'{resource_name} not found in report'
    assert another_user_name not in content, f'{another_user_name} found in report'


@freezegun.freeze_time(datetime.datetime(2025, 1, 1))
@pytest.mark.parametrize(
    'permissions',
    (
        pytest.param(['view_any_timesheet'], id='read_only'),
        pytest.param(['manage_any_timesheet'], id='read_write'),
        pytest.param(['view_any_timesheet', 'manage_any_timesheet'], id='both'),
    ),
)
@pytest.mark.parametrize('url', ('/be/report/', '/be/task_report/'))
def test_user_with_permissions_can_see_reports_of_all_resources_with_valid_contract(permissions, url, client):
    contracted_user = UserFactory(username='ihaveavalidcontract', password='pass123')
    preferred_user = UserFactory(username='ihaveonetoo', password='pass123')
    expired_user = UserFactory(username='former', password='pass123')
    user_without_contract = UserFactory(username='illegal', password='pass123')

    contracted_resource = ResourceFactory(user=contracted_user, profile=contracted_user.profile)
    preferred_resource = ResourceFactory(user=preferred_user, profile=preferred_user.profile, preferred_in_report=True)
    expired_resource = ResourceFactory(user=expired_user, profile=expired_user.profile, preferred_in_report=True)
    resource_without_contract = ResourceFactory(
        user=user_without_contract, profile=user_without_contract.profile, preferred_in_report=True
    )

    ContractFactory(
        resource=contracted_resource,
        period=(datetime.date(2024, 1, 1), None),
        work_schedule=WorkScheduleFactory(),
        meal_voucher_thresholds=MealVoucherThresholdsFactory(),
    )
    ContractFactory(
        resource=preferred_resource,
        period=(datetime.date(2024, 1, 1), None),
        work_schedule=WorkScheduleFactory(),
        meal_voucher_thresholds=MealVoucherThresholdsFactory(),
    )
    ContractFactory(
        resource=expired_resource,
        period=(datetime.date(2024, 1, 1), datetime.date(2024, 6, 1)),
        work_schedule=WorkScheduleFactory(),
        meal_voucher_thresholds=MealVoucherThresholdsFactory(),
    )

    def expected_rendered_name(resource):
        return f'{resource.last_name}</strong> {resource.first_name}'

    for permission in permissions:
        contracted_user.user_permissions.add(Permission.objects.get(codename=permission))
    client.login(username='ihaveavalidcontract', password='pass123')
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert expected_rendered_name(contracted_resource) in content
    assert expected_rendered_name(preferred_resource) in content
    assert expected_rendered_name(expired_resource) not in content
    assert expected_rendered_name(resource_without_contract) not in content


@pytest.mark.parametrize(
    'url', ('/be/home/', '/be/', '/be/availability/', '/be/report/', '/be/task_report/', '/be/releases/')
)
def test_unauthenticated_user_is_redirected_to_login_page(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f'/admin/login/?next={url}'
