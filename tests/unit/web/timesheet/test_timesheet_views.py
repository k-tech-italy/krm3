import datetime

import freezegun
import pytest
from django.contrib.auth.models import Permission

from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ResourceFactory, UserFactory
from testutils.web import _assert_homepage_content
from krm3.core.models import Contract


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

    _contract_for_contracted_resource = ContractFactory(resource=ResourceFactory(user=contracted_user) ,period=(_dt('2024-01-01'), None), contract_type=Contract.ContractType.EMPLOYEE)
    _contract_for_employed_resource = ContractFactory(period=(_dt('2024-01-01'), None), contract_type=Contract.ContractType.EMPLOYEE)
    _contract_for_expired_resource = ContractFactory(period=(_dt('2024-01-01'), _dt('2024-06-01')),contract_type=Contract.ContractType.CONTRACTOR)

    contracted_resource = _contract_for_contracted_resource.resource
    preferred_resource = _contract_for_employed_resource.resource
    expired_resource = _contract_for_expired_resource.resource
    resource_without_contract = ResourceFactory()

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
