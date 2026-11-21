import pytest
from django.urls import reverse
from testutils.factories import ResourceFactory, UserFactory

URL_NAME = 'core-api:user-me-preferred-language'


@pytest.mark.django_db
def test_get_preferred_language(api_client, regular_user):
    response = api_client(user=regular_user).get(reverse(URL_NAME))

    assert response.status_code == 200
    assert response.data == 'en-uk'


@pytest.mark.django_db
def test_update_preferred_language(api_client, regular_user):
    response = api_client(user=regular_user).patch(reverse(URL_NAME), data={'language_code': 'it'}, format='json')

    assert response.status_code == 200
    regular_user.profile.refresh_from_db()
    assert regular_user.profile.preferred_language == 'it'


@pytest.mark.django_db
def test_update_preferred_language_does_not_need_a_resource(api_client):
    user = UserFactory()
    assert user.get_resource() is None

    response = api_client(user=user).patch(reverse(URL_NAME), data={'language_code': 'fr'}, format='json')

    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.preferred_language == 'fr'


@pytest.mark.django_db
def test_update_preferred_language_changes_only_the_logged_in_user(api_client):
    user = ResourceFactory().user
    other_user = ResourceFactory().user

    response = api_client(user=user).patch(reverse(URL_NAME), data={'language_code': 'it'}, format='json')

    assert response.status_code == 200
    other_user.profile.refresh_from_db()
    assert other_user.profile.preferred_language == 'en-uk'


@pytest.mark.parametrize(
    'invalid_data',
    [
        pytest.param({}, id='empty-payload'),
        pytest.param({'language_code': ''}, id='empty-language-code'),
        pytest.param({'language_code': 'not a language code'}, id='wrong-code'),
        pytest.param({'language_code': None}, id='none'),
    ],
)
@pytest.mark.django_db
def test_update_preferred_language_rejects_invalid_data(api_client, regular_user, invalid_data):
    response = api_client(user=regular_user).patch(reverse(URL_NAME), data=invalid_data, format='json')

    assert response.status_code == 400
    regular_user.profile.refresh_from_db()
    assert regular_user.profile.preferred_language == 'en-uk'


@pytest.mark.parametrize('method', [pytest.param('get', id='get'), pytest.param('patch', id='patch')])
@pytest.mark.django_db
def test_preferred_language_requires_authentication(api_client, method):
    response = getattr(api_client(), method)(reverse(URL_NAME), data={'language_code': 'it'}, format='json')

    assert response.status_code in (401, 403)
