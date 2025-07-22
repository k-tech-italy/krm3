from django.urls import reverse

from django.contrib.auth import get_user_model
import pytest

def test_authenticated_user_should_see_navbar(client):
    get_user_model().objects.create_user(username='user00', password='pass123', email='email@gmail.com')
    client.login(username='user00', password='pass123')

    url = reverse("home")
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()

    report_expected_url = reverse('admin:core_timeentry_report')
    task_report_expected_url = reverse('admin:core_timeentry_task_report')

    assert 'Report' in content
    assert 'Report by task' in content
    assert f'href="{report_expected_url}"' in content
    assert f'href="{task_report_expected_url}"' in content

@pytest.mark.parametrize(
    'url', ('/be/home/', '/be/')
)
def test_not_authenticated_user_should_be_redirected_to_login_page(client, url):

    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f'/admin/login/?next={url}'
