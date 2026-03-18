import pytest
from django.urls import reverse

from testutils.factories import ResourceFactory


@pytest.mark.django_db
def test_get_preferred_language(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    assert resource.preferred_language == 'en-uk'

    response = client.get(reverse('core-api:api-resources-preferred-language', args=[resource.pk]))

    assert response.status_code == 200
    assert response.data == 'en-uk'


@pytest.mark.django_db
def test_update_preferred_language(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    assert resource.preferred_language == 'en-uk'

    response = client.patch(
        reverse('core-api:api-resources-preferred-language', args=[resource.pk]),
        data={'language_code': 'it'},
        content_type='application/json'
    )

    assert response.status_code == 200

    resource.refresh_from_db()
    assert resource.preferred_language == 'it'


@pytest.mark.parametrize(
        'invalid_data',
        (pytest.param({}, id='empty payload'),
         pytest.param({'language_code': ''}, id='empty language_code'),
         pytest.param({'language_code': 'not a language code'}, id='wrong code'),
         pytest.param({'language_code': None}, id='None'),
         ),
    )
@pytest.mark.django_db
def test_update_preferred_language_missing_code(django_client_and_auth_resource, invalid_data):
    client, resource = django_client_and_auth_resource

    response = client.patch(
        reverse('core-api:api-resources-preferred-language', args=[resource.pk]),
        data=invalid_data,
        content_type='application/json'
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_update_preferred_language_other_user(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    another_resource = ResourceFactory()

    response = client.patch(
        reverse('core-api:api-resources-preferred-language', args=[another_resource.pk]),
        data={'language_code': 'it'},
        content_type='application/json'
    )

    assert response.status_code == 403
    assert response.data.get('detail') == 'You do not have permission to perform this action.'

    another_resource.refresh_from_db()
    assert another_resource.preferred_language == 'en-uk'