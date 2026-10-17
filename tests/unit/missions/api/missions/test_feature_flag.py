import pytest
from rest_framework.reverse import reverse
from testutils.factories import ExpenseFactory, MissionFactory

ENDPOINTS = [
    pytest.param('missions-api:mission-list', id='mission'),
    pytest.param('missions-api:expense-list', id='expense'),
    pytest.param('missions-api:expensecategory-list', id='expense-category'),
    pytest.param('missions-api:paymentcategory-list', id='payment-category'),
    pytest.param('missions-api:documenttype-list', id='document-type'),
]


@pytest.fixture
def missions_disabled(settings):
    settings.FLAGS = {**settings.FLAGS, 'TRASFERTE_ENABLED': [('boolean', False)]}


@pytest.mark.parametrize('url_name', ENDPOINTS)
def test_missions_api_available_when_flag_enabled(api_client, admin_user, url_name):
    response = api_client(user=admin_user).get(reverse(url_name))

    assert response.status_code == 200


@pytest.mark.parametrize('url_name', ENDPOINTS)
def test_missions_api_forbidden_when_flag_disabled(api_client, admin_user, missions_disabled, url_name):
    response = api_client(user=admin_user).get(reverse(url_name))

    assert response.status_code == 403
    assert response.json()['detail'] == 'This feature is not enabled.'


def test_mission_detail_forbidden_when_flag_disabled(api_client, admin_user, missions_disabled):
    mission = MissionFactory()

    response = api_client(user=admin_user).get(reverse('missions-api:mission-detail', args=[mission.pk]))

    assert response.status_code == 403


def test_expense_check_ts_forbidden_when_flag_disabled(api_client, missions_disabled):
    expense = ExpenseFactory()

    response = api_client().get(reverse('missions-api:expense-check-ts', args=[expense.pk]), {'ms': 0})

    assert response.status_code == 403


def test_missions_api_flag_by_group(api_client, regular_user, settings):
    from testutils.factories import GroupFactory  # noqa: PLC0415

    settings.FLAGS = {**settings.FLAGS, 'TRASFERTE_ENABLED': [('has group', 'missions')]}
    url = reverse('missions-api:mission-list')

    assert api_client(user=regular_user).get(url).status_code == 403

    regular_user.groups.add(GroupFactory(name='missions'))
    assert api_client(user=regular_user).get(url).status_code == 200
