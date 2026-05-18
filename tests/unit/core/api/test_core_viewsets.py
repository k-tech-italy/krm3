from django.contrib.auth.models import Permission
import pytest
from rest_framework.reverse import reverse
from rest_framework import status


from krm3.utils.dates import KrmDay, KrmDateRange
from testutils.factories import ResourceFactory, ContractFactory

@pytest.mark.parametrize(
    "contracts, query_period, expected",
    [
        pytest.param([], (None, None), 0, id='no_contracts'),
        pytest.param([
            ('2024-02-14','2024-03-01'),
        ], ('2024-03-01', None), 0, id='before_contract'),
        pytest.param([
            ('2024-02-14', '2024-03-02'),
        ], ('2024-03-01', None), 1, id='lower_contract'),
        pytest.param([
            ('2024-02-14', '2024-03-01'), ('2024-03-16', None)
        ], ('2024-03-01', '2024-03-15'), 0, id='outside_contracts'),
        pytest.param([
            ('2024-02-14', '2024-03-02'),
            ('2024-03-16', None)
        ], ('2024-03-01', '2024-03-31'), 1, id='multi_contract'),
    ]
)
def test_can_request_active_resources(
        contracts,
        query_period,
        expected,
        resource, regular_user,
        api_client,
):
    for contract in contracts:
        ContractFactory(resource=resource, period=KrmDateRange(contract))

    range = KrmDateRange.from_start_end(*query_period).boundaries
    range = range[0] or "", range[1] or ""
    url = reverse('core-api:api-resources-active', args=range)
    response = api_client(user=regular_user).get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data == [
        {'id': resource.id,
         'first_name': resource.first_name,
         'last_name': resource.last_name}] * expected
