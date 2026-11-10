import pytest
from django.urls import reverse

from krm3.utils.environments import environment_info


@pytest.mark.parametrize(
    ('environment', 'expected'),
    [
        pytest.param(
            'local',
            {'environment': 'local', 'show_banner': True, 'label': 'LOCAL', 'color': '#fed7aa'},
            id='local',
        ),
        pytest.param(
            'int',
            {'environment': 'int', 'show_banner': True, 'label': 'INT', 'color': '#86efac'},
            id='int',
        ),
        pytest.param(
            'INT',
            {'environment': 'int', 'show_banner': True, 'label': 'INT', 'color': '#86efac'},
            id='int-uppercase',
        ),
        pytest.param(
            'staging',
            {'environment': 'staging', 'show_banner': True, 'label': 'STAGING', 'color': '#86efac'},
            id='staging',
        ),
        pytest.param(
            'production',
            {'environment': 'production', 'show_banner': False, 'label': '', 'color': ''},
            id='production',
        ),
        pytest.param(
            'prod',
            {'environment': 'prod', 'show_banner': False, 'label': '', 'color': ''},
            id='prod',
        ),
        pytest.param(
            ' Production ',
            {'environment': 'production', 'show_banner': False, 'label': '', 'color': ''},
            id='production-padded',
        ),
    ],
)
def test_environment_info(environment, expected):
    assert environment_info(environment) == expected


@pytest.mark.django_db
def test_api_response_carries_environment_headers(api_client, regular_user, settings):
    settings.SENTRY_ENVIRONMENT = 'local'
    response = api_client(user=regular_user).get(reverse('languages-list'))
    assert response.status_code == 200
    assert response['X-environment'] == 'local'
    assert response['X-env-color'] == '#fed7aa'


@pytest.mark.django_db
def test_api_response_carries_environment_headers_when_not_authenticated(client, settings):
    # The FE reads the headers from the login-page probe response, which is not authenticated.
    settings.SENTRY_ENVIRONMENT = 'local'
    response = client.get(reverse('languages-list'))
    assert response.status_code == 403
    assert response['X-environment'] == 'local'
    assert response['X-env-color'] == '#fed7aa'


@pytest.mark.django_db
def test_non_api_response_has_no_environment_headers(client):
    response = client.get(reverse('admin:login'))
    assert response.status_code == 200
    assert 'X-environment' not in response
    assert 'X-env-color' not in response


@pytest.mark.parametrize(
    ('environment', 'color'),
    [
        pytest.param('local', '#fed7aa', id='local'),
        pytest.param('int', '#86efac', id='int'),
        pytest.param('production', '', id='production'),
    ],
)
@pytest.mark.django_db
def test_environment_headers_matrix(api_client, regular_user, settings, environment, color):
    settings.SENTRY_ENVIRONMENT = environment
    response = api_client(user=regular_user).get(reverse('languages-list'))
    assert response.status_code == 200
    assert response['X-environment'] == environment
    assert response.get('X-env-color', '') == color
