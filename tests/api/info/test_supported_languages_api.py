import pytest
from django.urls import reverse
from django.conf import settings
import django.test as django_test

@django_test.override_settings(LANGUAGES = [
    ('en-uk', 'English'),
    ('it', 'Italiano'),
    ('fr', 'Français'),
    ('pl', 'Polski'),
])
@pytest.mark.django_db
def test_get_supported_languages(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource

    response = client.get(reverse('languages-list'))
    assert response.status_code == 200

    # Format languages in the same way as the api
    expected = [
        {"language_code": code, "language": name}
        for code, name in settings.LANGUAGES
    ]
    assert response.data == expected
