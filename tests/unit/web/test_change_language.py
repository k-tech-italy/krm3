import pytest
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.conf import settings


User = get_user_model()


@pytest.mark.db
def test_language_change_happy_path(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    assert resource.preferred_language == 'pl', "Sanity check, ResourceFactory should be setting this."

    home_response = client.get('/')
    home_cookie = home_response.cookies.get(settings.LANGUAGE_COOKIE_NAME)
    assert home_cookie.coded_value == 'pl', "Verify the set up - language cookie"
    assert home_response.LANGUAGE_CODE == 'pl', "Verify the set up - response language code"


    response = client.post(
        reverse('user_resource', args=[resource.user.id]),
        data={
            'first_name': resource.first_name,
            'last_name': resource.last_name,
            'preferred_language': 'it'
        }
    )

    language_cookie = response.cookies.get(settings.LANGUAGE_COOKIE_NAME)
    assert language_cookie.coded_value == 'it', "Check the language cookie has been updated."
    assert response.LANGUAGE_CODE == 'it', "Check the language code has been updated."

    admin_panel_body = client.get('/admin/').content.decode()
    assert 'Benvenuto' in admin_panel_body, "Check that the language has been updated."
