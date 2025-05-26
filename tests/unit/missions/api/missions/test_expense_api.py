from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.reverse import reverse

from testutils.factories import MissionFactory, ExpenseFactory


def test_api_view_own_expenses(api_client, expense, regular_user, resource):
    User = get_user_model()  # noqa: N806
    url = reverse('missions-api:expense-list')

    resource.user = regular_user
    resource.save()
    my_mission = MissionFactory(resource=resource)
    my_expense = ExpenseFactory(mission=my_mission)

    client = api_client(user=regular_user)
    response = client.get(url)

    assert response.status_code == 200
    response_data = dict(response.data)

    assert response_data['count'] == 1
    assert response_data['results'][0]['id'] == my_expense.id

    regular_user.user_permissions.add(Permission.objects.get(codename='view_any_expense').id)
    user = User.objects.get(id=regular_user.id)  # invalidate cache
    client = api_client(user=user)
    response = client.get(url)

    assert response.status_code == 200
    response_data = dict(response.data)
    assert response_data['count'] == 2


def test_api_admin_view_all_expenses(api_client, expense, regular_user, admin_user, resource):
    url = reverse('missions-api:expense-list')

    other_mission = MissionFactory(resource=resource)
    other_expense = ExpenseFactory(mission=other_mission)

    client = api_client(user=admin_user)
    response = client.get(url)

    assert response.status_code == 200
    response_data = dict(response.data)

    assert response_data['count'] == 2
    assert {x['id'] for x in response_data['results']} == {other_expense.id, expense.id}
