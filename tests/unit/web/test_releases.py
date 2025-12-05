from unittest.mock import patch

from django.urls import reverse
from testutils.factories import UserFactory


@patch(
    'pathlib.Path.read_text',
    return_value="""## 1.5.33 (2025-09-10)
        ### Fix
        - update template

        ## 1.5.32 (2025-09-09)

        ### Feat
        - add commitizen setup

        ### Fix
        - update bump command with interactive mode""",
)
def test_releases_view_with_valid_markdown(mock_file, client):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    response = client.get(reverse('releases'))
    content = response.content.decode()

    assert response.status_code == 200
    assert '1.5.33' in content
    assert '1.5.32' in content
    assert 'update template' in content
    assert 'add commitizen setup' in content
    assert 'update bump command' in content
    assert 'Changelog' in content


@patch('pathlib.Path.read_text', side_effect=FileNotFoundError())
def test_releases_view_with_missing_file_should_show_error(mock_open_func, client):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    response = client.get(reverse('releases'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'text-gray-400' in content
    assert 'CHANGELOG.md file not found' in content


@patch('pathlib.Path.read_text', side_effect=PermissionError())
def test_releases_view_with_file_read_error(mock_open_func, client):
    UserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')

    response = client.get(reverse('releases'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Changelog' in content
    assert 'Error parsing CHANGELOG.md' in content
