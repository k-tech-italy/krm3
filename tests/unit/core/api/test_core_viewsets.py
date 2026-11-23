import pytest
from freezegun import freeze_time
from ktcalendars import KTDateRange
from rest_framework import status
from rest_framework.reverse import reverse
from testutils.factories import ContractFactory, ProjectFactory, TaskFactory


@freeze_time('2026-09-07')
def test_can_request_active_resources_for_current_month_by_default(resource, regular_user, api_client):
    ContractFactory(resource=resource, period=KTDateRange('2026-09-01', None))
    ContractFactory(period=KTDateRange('2026-07-01', '2026-08-31'))

    response = api_client(user=regular_user).get('/api/v1/core/resource/active/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data == [{'id': resource.id, 'first_name': resource.first_name, 'last_name': resource.last_name}]


@pytest.mark.parametrize(
    'contracts, query_period, expected',
    [
        pytest.param([], ('1900-01-01', '2100-12-31'), 0, id='no_contracts'),
        pytest.param(
            [
                ('2024-02-14', '2024-03-01'),
            ],
            ('2024-03-01', '2025-03-01'),
            0,
            id='before_contract',
        ),
        pytest.param(
            [
                ('2024-02-14', '2024-03-02'),
            ],
            ('2024-03-01', '2025-03-01'),
            1,
            id='lower_contract',
        ),
        pytest.param(
            [('2024-02-14', '2024-03-01'), ('2024-03-16', None)],
            ('2024-03-01', '2024-03-15'),
            0,
            id='outside_contracts',
        ),
        pytest.param(
            [('2024-02-14', '2024-03-02'), ('2024-03-16', None)], ('2024-03-01', '2024-03-31'), 1, id='multi_contract'
        ),
    ],
)
def test_can_request_active_resources(  # noqa: PLR0917
    contracts,
    query_period,
    expected,
    resource,
    regular_user,
    api_client,
):
    for contract in contracts:
        ContractFactory(resource=resource, period=KTDateRange(*contract))

    url = reverse('core-api:api-resources-active', args=query_period)
    response = api_client(user=regular_user).get(url)
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.data
        == [{'id': resource.id, 'first_name': resource.first_name, 'last_name': resource.last_name}] * expected
    )


@freeze_time('2026-09-07')
@pytest.mark.parametrize(
    'task_periods, listed',
    [
        pytest.param([('2026-01-01', '2026-09-07')], False, id='ended-yesterday'),
        pytest.param([('2026-01-01', '2026-09-08')], True, id='ends-today'),
        pytest.param([('2026-01-01', None)], True, id='open-ended'),
        pytest.param([('2026-10-01', '2026-11-01')], True, id='future'),
        pytest.param([('2026-01-01', None), ('2026-10-01', None)], True, id='many-tasks-listed-once'),
    ],
)
def test_projects_filtered_by_resource_involvement(task_periods, listed, resource, regular_user, api_client):
    ContractFactory(resource=resource, period=KTDateRange('2026-01-01', None))
    project = ProjectFactory(period=KTDateRange('2026-01-01', None))
    for i, period in enumerate(task_periods):
        TaskFactory(project=project, resource=resource, title=f'task {i}', period=KTDateRange(*period))
    TaskFactory(period=KTDateRange('2026-01-01', None), contract=True)  # another resource's project

    response = api_client(user=regular_user).get('/api/v1/core/project/', {'resource': resource.pk})

    assert response.status_code == status.HTTP_200_OK
    assert [p['id'] for p in response.data['results']] == ([project.pk] if listed else [])


def test_project_resource_filter_rejects_non_integer(regular_user, api_client):
    response = api_client(user=regular_user).get('/api/v1/core/project/', {'resource': 'x'})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
