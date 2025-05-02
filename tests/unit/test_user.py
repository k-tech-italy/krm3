from django.urls import reverse


def test_login_ok(api_client, regular_user):
    url = reverse('core-api:user-login')
    response = api_client().post(
        url, data={'username': regular_user.username, 'password': 'password'}, content_type='application/json'
    )
    assert response.status_code == 200


def test_login_nok(api_client, regular_user):
    url = reverse('core-api:user-login')
    response = api_client().post(
        url, data={'username': regular_user.username, 'password': 'wrong'}, content_type='application/json'
    )
    assert response.status_code == 401
