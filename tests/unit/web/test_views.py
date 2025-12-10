import datetime

import freezegun
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from testutils.factories import ContractFactory, ResourceFactory, UserFactory


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
def test_resource_user_should_see_all_be_views(resource_client, url):
    response = resource_client.get(url)
    _assert_homepage_content(response)


@pytest.mark.parametrize(
    'url',
    [
        pytest.param('/be/report/', id='report'),
        pytest.param('/be/task_report/', id='task_report'),
    ],
)
def test_user_without_permission_should_only_see_its_reports(url, resource_client):
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
@pytest.mark.parametrize('url', ('/be/report/', '/be/task_report/'))
def test_user_with_permissions_should_see_reports_of_all_resources_with_valid_contract(url, client):
    contracted_user = UserFactory(username='user00', password='pass123')
    preferred_user = UserFactory(username='user01', password='pass123')
    expired_user = UserFactory(username='former', password='pass123')
    user_without_contract = UserFactory(username='illegal', password='pass123')

    contracted_resource = ResourceFactory(user=contracted_user, profile=contracted_user.profile)
    preferred_resource = ResourceFactory(user=preferred_user, profile=preferred_user.profile, preferred_in_report=True)
    expired_resource = ResourceFactory(user=expired_user, profile=expired_user.profile, preferred_in_report=True)
    _resource_without_contract = ResourceFactory(
        user=user_without_contract, profile=user_without_contract.profile, preferred_in_report=True
    )

    _contract_for_contracted_resource = ContractFactory(
        resource=contracted_resource, period=(datetime.date(2024, 1, 1), None)
    )
    _contract_for_preferred_resource = ContractFactory(
        resource=preferred_resource, period=(datetime.date(2024, 1, 1), None)
    )
    _contract_for_expired_resource = ContractFactory(
        resource=expired_resource, period=(datetime.date(2024, 1, 1), datetime.date(2024, 6, 1))
    )

    def expected_rendered_name(resource):
        return f'{resource.last_name}</strong> {resource.first_name}'

    for perm in ['manage_any_timesheet', 'view_any_timesheet']:
        contracted_user.user_permissions.add(Permission.objects.get(codename=perm))
        client.login(username='user00', password='pass123')
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        contracted_expected_name = expected_rendered_name(contracted_resource)
        preferred_expected_name = expected_rendered_name(preferred_resource)
        assert contracted_expected_name in content
        assert preferred_expected_name in content


@pytest.mark.parametrize(
    'url', ('/be/home/', '/be/', '/be/availability/', '/be/report/', '/be/task_report/', '/be/releases/')
)
def test_not_authenticated_user_should_be_redirected_to_login_page(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f'/admin/login/?next={url}'
