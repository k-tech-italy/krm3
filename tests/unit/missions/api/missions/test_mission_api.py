import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.reverse import reverse

from testutils.factories import MissionFactory

from krm3.core.models import Mission


class TestMissionApiPermissions:
    def test_api_view_own_missions(self, api_client, mission, regular_user, resource):
        User = get_user_model()  # noqa: N806
        url = reverse('missions-api:mission-list')

        resource.user = regular_user
        resource.save()
        _ = MissionFactory(resource=resource)

        client = api_client(user=regular_user)
        response = client.get(url)

        assert response.status_code == 200
        response_data = dict(response.data)

        assert response_data['count'] == 1
        assert response_data['results'][0]['resource']['id'] == resource.id

        regular_user.user_permissions.add(Permission.objects.get(codename='view_any_mission').id)
        user = User.objects.get(id=regular_user.id)  # invalidate cache
        client = api_client(user=user)
        response = client.get(url)

        assert response.status_code == 200
        response_data = dict(response.data)

        assert response_data['count'] == 2

    def test_api_admin_view_all_missions(self, api_client, mission, regular_user, admin_user, resource):
        url = reverse('missions-api:mission-list')

        other_mission = MissionFactory(resource=resource)

        client = api_client(user=admin_user)
        response = client.get(url)

        assert response.status_code == 200
        response_data = dict(response.data)

        assert response_data['count'] == 2
        assert {x['resource']['id'] for x in response_data['results']} == {
            other_mission.resource.id,
            mission.resource.id,
        }

    def test_api_view_mission_response(self, api_client, regular_user, resource):
        url = reverse('missions-api:mission-list')

        resource.user = regular_user
        resource.save()
        _ = MissionFactory(resource=resource)

        client = api_client(user=regular_user)
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()['results'][0]['resource']['id'] == resource.id
        assert response.json()['results'][0]['resource']['user'] == resource.user.id


class TestMissionApiCreate:
    @staticmethod
    def _payload(**overrides):
        from testutils.factories import CityFactory, ProjectFactory, ResourceFactory  # noqa: PLC0415

        return {
            'fromDate': '2024-01-02',
            'toDate': '2024-01-05',
            'project': ProjectFactory().id,
            'city': CityFactory().id,
            'resource': ResourceFactory().id,
        } | overrides

    def test_create_mission_is_draft_without_number(self, api_client, admin_user):
        MissionFactory(number=1, year=2024)  # an existing submitted mission must not influence the draft

        response = api_client(user=admin_user).post(
            reverse('missions-api:mission-list'), self._payload(number=99), format='json'
        )

        assert response.status_code == 201, response.data
        mission = Mission.objects.get(status=Mission.MissionStatus.DRAFT)
        assert (mission.status, mission.number, mission.year) == (Mission.MissionStatus.DRAFT, None, 2024)

    def test_create_mission_invalid_dates_returns_400(self, api_client, admin_user):
        response = api_client(user=admin_user).post(
            reverse('missions-api:mission-list'), self._payload(toDate='2024-01-01'), format='json'
        )

        assert response.status_code == 400


class TestMissionApiSubmit:
    @staticmethod
    def _url(mission):
        return reverse('missions-api:mission-submit', args=[mission.pk])

    def test_owner_submits_draft(self, api_client, regular_user, resource):
        from testutils.date_utils import _dt  # noqa: PLC0415

        resource.user = regular_user
        resource.save()
        MissionFactory(number=1, from_date=_dt('2024-02-01'))
        draft = MissionFactory(resource=resource, number=None, status='DRAFT', from_date=_dt('2024-03-01'))

        response = api_client(user=regular_user).post(self._url(draft))

        assert response.status_code == 200, response.data
        assert (response.data['status'], response.data['number']) == (Mission.MissionStatus.SUBMITTED, 2)

    def test_submit_already_submitted_returns_400(self, api_client, admin_user):
        mission = MissionFactory(number=1)

        response = api_client(user=admin_user).post(self._url(mission))

        assert response.status_code == 400

    @pytest.mark.parametrize(
        ('perm', 'expected'),
        [
            pytest.param('view_any_mission', 403, id='view-only'),
            pytest.param('manage_any_mission', 200, id='manager'),
        ],
    )
    def test_submit_someone_else_mission(self, api_client, regular_user, perm, expected):
        regular_user.user_permissions.add(Permission.objects.get(codename=perm))
        user = get_user_model().objects.get(id=regular_user.id)  # invalidate cache
        draft = MissionFactory(number=None, status='DRAFT')

        response = api_client(user=user).post(self._url(draft))

        assert response.status_code == expected

    def test_cannot_submit_invisible_mission(self, api_client, regular_user):
        draft = MissionFactory(number=None, status='DRAFT')

        response = api_client(user=regular_user).post(self._url(draft))

        assert response.status_code == 404
