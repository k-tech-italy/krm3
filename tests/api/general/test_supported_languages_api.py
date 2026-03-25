import pytest
from django.urls import reverse
from django.conf import settings


@pytest.mark.django_db
def test_get_supported_languages(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource

    response = client.get(reverse('core-api:supported-languages-list'))

    assert response.status_code == 200

    expected = [
        {"language_code": code, "language": name}
        for code, name in settings.LANGUAGES
    ]
    assert response.data == expected