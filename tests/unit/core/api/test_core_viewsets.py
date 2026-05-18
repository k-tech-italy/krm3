import pytest
from ktcalendars import KTDateRange
from rest_framework import status
from rest_framework.reverse import reverse
from testutils.factories import ContractFactory

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
def test_can_request_active_resources(
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
