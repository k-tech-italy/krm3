import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from testutils.factories import UserFactory


class TestGoogleOAuthView:
    @staticmethod
    def url(backend='google-oauth2'):
        return reverse('oauth', kwargs={'backend': backend})

    def test_get_missing_redirect_uri(self):
        client = APIClient()
        response = client.get(self.url())

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['error'] == 'redirect_uri is required'

    @pytest.mark.django_db
    @patch('social_django.utils.load_strategy')
    @patch('social_django.utils.load_backend')
    def test_get_returns_authorization_url(self, mock_load_backend, mock_load_strategy):
        redirect_uri = 'http://localhost:8000/login'
        mock_backend = MagicMock()
        mock_backend.state_token.return_value = 'state-token'
        mock_backend.auth_url.return_value = 'https://accounts.google.com/oauth/auth'
        mock_load_backend.return_value = mock_backend

        client = APIClient()
        response = client.get(self.url(), {'redirect_uri': redirect_uri})

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'authorization_url': 'https://accounts.google.com/oauth/auth'}
        assert 'google-oauth2_state' in client.session
        mock_load_strategy.assert_called_once()
        mock_load_backend.assert_called_once_with(
            mock_load_strategy.return_value,
            'google-oauth2',
            redirect_uri=redirect_uri,
        )
        mock_backend.auth_url.assert_called_once()

    def test_post_missing_state(self):
        client = APIClient()
        response = client.post(self.url(), {'code': 'auth-code'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['error'] == 'State parameter is required'

    @pytest.mark.django_db
    def test_post_invalid_state(self):
        client = APIClient()
        response = client.post(
            self.url(), {'state': 'not-valid-base64!!!', 'code': 'auth-code'}, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['error'] == 'Failed to decode state.'

    @pytest.mark.django_db
    def test_post_state_mismatch(self):
        client = APIClient()
        session = client.session
        session['google-oauth2_state'] = 'different-state'
        session.save()

        state_data = {'redirect_uri': 'http://localhost:8000/login', 'state': 'state-token'}
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        response = client.post(
            self.url(), {'state': encoded_state, 'code': 'auth-code'}, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['error'] == 'State mismatch. Possible CSRF attack.'

    @pytest.mark.django_db
    @patch('social_django.utils.load_strategy')
    @patch('social_django.utils.load_backend')
    def test_post_success(self, mock_load_backend, mock_load_strategy):
        user = UserFactory()

        mock_backend = MagicMock()
        mock_backend.complete.return_value = user
        mock_load_backend.return_value = mock_backend

        redirect_uri = 'http://localhost:8000/login'
        state_data = {'redirect_uri': redirect_uri, 'state': 'state-token'}
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        client = APIClient()
        session = client.session
        session['google-oauth2_state'] = encoded_state
        session.save()

        response = client.post(
            self.url(), {'state': encoded_state, 'code': 'auth-code'}, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['detail'] == 'Login successful'
        assert response.json()['user']['id'] == user.id
        assert 'google-oauth2_state' not in client.session
        assert mock_load_strategy.called
        mock_load_backend.assert_called_once_with(
            mock_load_strategy.return_value,
            'google-oauth2',
            redirect_uri=redirect_uri,
        )
        mock_backend.complete.assert_called_once_with(user=None)

    @pytest.mark.django_db
    @patch('social_django.utils.load_strategy')
    @patch('social_django.utils.load_backend')
    def test_post_authentication_failed(self, mock_load_backend, mock_load_strategy):
        mock_backend = MagicMock()
        mock_backend.complete.return_value = None
        mock_load_backend.return_value = mock_backend

        redirect_uri = 'http://localhost:8000/login'
        state_data = {'redirect_uri': redirect_uri, 'state': 'state-token'}
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        client = APIClient()
        session = client.session
        session['google-oauth2_state'] = encoded_state
        session.save()

        response = client.post(
            self.url(), {'state': encoded_state, 'code': 'auth-code'}, format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()['error'] == 'Authentication failed'
