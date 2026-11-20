"""Filters, ordering and pagination of the missions and expenses list endpoints (taiga#739)."""

import datetime

import pytest
from django.contrib.auth.models import Permission
from rest_framework.reverse import reverse

from testutils.factories import (
    CityFactory,
    CountryFactory,
    ExpenseCategoryFactory,
    ExpenseFactory,
    MissionFactory,
    ProjectFactory,
    ResourceFactory,
    UserFactory,
)

MISSIONS_URL = reverse('missions-api:mission-list')
EXPENSES_URL = reverse('missions-api:expense-list')

D = datetime.date


def _ids(response) -> list[int]:
    assert response.status_code == 200, response.content
    return [item['id'] for item in response.json()['results']]


def _user_with(*codenames: str):
    user = UserFactory()
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


@pytest.fixture
def missions(db):
    """Three missions of two resources, with distinct dates, statuses and places."""
    alice = ResourceFactory(first_name='Alice', last_name='Rossi')
    bob = ResourceFactory(first_name='Bob', last_name='Bianchi')
    paris = CityFactory(name='Paris', country=CountryFactory(name='France'))
    rome = CityFactory(name='Rome', country=CountryFactory(name='Italy'))
    return {
        'draft': MissionFactory(
            resource=alice,
            city=paris,
            status='DRAFT',
            number=None,
            from_date=D(2024, 1, 10),
            to_date=D(2024, 1, 12),
            title='Kickoff',
            project=ProjectFactory(name='Apollo'),
        ),
        'submitted': MissionFactory(
            resource=bob,
            city=rome,
            status='SUBMITTED',
            number=7,
            from_date=D(2024, 3, 1),
            to_date=D(2024, 3, 5),
            title='Audit',
        ),
        'cancelled': MissionFactory(
            resource=alice,
            city=rome,
            status='CANCELLED',
            number=3,
            from_date=D(2025, 6, 1),
            to_date=D(2025, 6, 2),
            title='Workshop',
        ),
    }


@pytest.fixture
def manager_client(api_client):
    return api_client(user=_user_with('manage_any_mission', 'manage_any_expense'))


class TestMissionFilters:
    @pytest.mark.parametrize(
        ('params', 'expected'),
        [
            pytest.param({}, ['cancelled', 'submitted', 'draft'], id='no-filter-newest-first'),
            pytest.param({'status': 'DRAFT,SUBMITTED'}, ['submitted', 'draft'], id='status-many'),
            pytest.param({'status': 'CANCELLED'}, ['cancelled'], id='status-one'),
            pytest.param({'dateFrom': '2024-01-11', 'dateTo': '2024-03-01'}, ['submitted', 'draft'], id='overlap'),
            pytest.param({'dateFrom': '2024-01-13'}, ['cancelled', 'submitted'], id='date-from-only'),
            pytest.param({'dateTo': '2024-01-10'}, ['draft'], id='date-to-only'),
            pytest.param({'year': '2025'}, ['cancelled'], id='year'),
            pytest.param({'number': '7', 'year': '2024'}, ['submitted'], id='number-and-year'),
            pytest.param({'search': 'paris'}, ['draft'], id='search-city'),
            pytest.param({'search': 'italy'}, ['cancelled', 'submitted'], id='search-country'),
            pytest.param({'search': 'apollo'}, ['draft'], id='search-project'),
            pytest.param({'search': 'alice rome'}, ['cancelled'], id='search-all-words'),
            pytest.param({'search': 'audit'}, ['submitted'], id='search-title'),
            pytest.param({'search': '3'}, ['cancelled'], id='search-number'),
        ],
    )
    def test_filter(self, manager_client, missions, params, expected):
        assert _ids(manager_client.get(MISSIONS_URL, params)) == [missions[k].id for k in expected]

    def test_filter_by_resource(self, manager_client, missions):
        resource_id = missions['submitted'].resource_id
        assert _ids(manager_client.get(MISSIONS_URL, {'resource': str(resource_id)})) == [missions['submitted'].id]

        both = f'{resource_id},{missions["draft"].resource_id}'
        assert len(_ids(manager_client.get(MISSIONS_URL, {'resource': both}))) == 3

    @pytest.mark.parametrize(
        ('ordering', 'expected'),
        [
            pytest.param('fromDate', ['draft', 'submitted', 'cancelled'], id='from-date'),
            pytest.param('-toDate', ['cancelled', 'submitted', 'draft'], id='to-date-desc'),
            pytest.param('title', ['submitted', 'draft', 'cancelled'], id='title'),
            pytest.param('resource,fromDate', ['submitted', 'draft', 'cancelled'], id='resource-then-date'),
            pytest.param('status,fromDate', ['cancelled', 'draft', 'submitted'], id='status'),
        ],
    )
    def test_ordering(self, manager_client, missions, ordering, expected):
        assert _ids(manager_client.get(MISSIONS_URL, {'ordering': ordering})) == [missions[k].id for k in expected]

    def test_page_size(self, manager_client, missions):
        response = manager_client.get(MISSIONS_URL, {'pageSize': 2, 'page': 2})
        assert response.json()['count'] == 3
        assert _ids(response) == [missions['draft'].id]

    def test_detail_ignores_filters(self, manager_client, missions):
        """Filters only narrow the list: a filtered-out mission is still reachable by id."""
        url = reverse('missions-api:mission-detail', args=[missions['cancelled'].id])
        assert manager_client.get(url, {'status': 'DRAFT'}).status_code == 200


class TestMissionResourceFilterPermissions:
    """The resource filter never widens what `filter_acl` lets the user see."""

    @pytest.mark.parametrize(
        ('codenames', 'sees_other'),
        [
            pytest.param((), False, id='no-permission'),
            pytest.param(('view_any_mission',), True, id='view-only'),
            pytest.param(('manage_any_mission',), True, id='manager'),
        ],
    )
    def test_matrix(self, api_client, missions, codenames, sees_other):
        user = _user_with(*codenames)
        own = MissionFactory(resource=ResourceFactory(user=user), from_date=D(2023, 1, 1), to_date=D(2023, 1, 2))
        other = missions['submitted']
        client = api_client(user=user)

        # owner: always sees their own missions through the filter
        assert _ids(client.get(MISSIONS_URL, {'resource': str(own.resource_id)})) == [own.id]
        expected_other = [other.id] if sees_other else []
        assert _ids(client.get(MISSIONS_URL, {'resource': str(other.resource_id)})) == expected_other


class TestExpenseFilters:
    @pytest.fixture
    def expenses(self, missions):
        food = ExpenseCategoryFactory(title='Food')
        return {
            'early': ExpenseFactory(mission=missions['draft'], day=D(2024, 1, 10), detail='Taxi', amount_currency=10),
            'late': ExpenseFactory(mission=missions['submitted'], day=D(2024, 3, 2), category=food, amount_currency=5),
        }

    @pytest.mark.parametrize(
        ('params', 'expected'),
        [
            pytest.param({}, ['late', 'early'], id='no-filter-newest-first'),
            pytest.param({'dateFrom': '2024-02-01'}, ['late'], id='date-from'),
            pytest.param({'dateTo': '2024-02-01'}, ['early'], id='date-to'),
            pytest.param({'search': 'taxi'}, ['early'], id='search-detail'),
            pytest.param({'search': 'food'}, ['late'], id='search-category'),
            pytest.param({'search': 'bianchi'}, ['late'], id='search-resource'),
            pytest.param({'ordering': 'amountCurrency'}, ['late', 'early'], id='ordering-amount'),
            pytest.param({'ordering': '-resource'}, ['early', 'late'], id='ordering-resource'),
        ],
    )
    def test_filter(self, manager_client, expenses, params, expected):
        assert _ids(manager_client.get(EXPENSES_URL, params)) == [expenses[k].id for k in expected]

    def test_filter_by_mission_and_resource(self, manager_client, expenses, missions):
        expected = [expenses['early'].id]
        assert _ids(manager_client.get(EXPENSES_URL, {'mission': str(missions['draft'].id)})) == expected
        assert _ids(manager_client.get(EXPENSES_URL, {'resource': str(missions['draft'].resource_id)})) == expected

    def test_list_has_mission_title_and_resource_name(self, manager_client, expenses):
        item = manager_client.get(EXPENSES_URL, {'search': 'taxi'}).json()['results'][0]
        assert item['missionTitle'] == 'Kickoff'
        assert item['resourceName'] == 'Alice Rossi'
