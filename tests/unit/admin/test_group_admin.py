import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from testutils.factories import UserFactory


@pytest.fixture
def group():
    return Group.objects.create(name='Accounting')


def _members_url(group: Group) -> str:
    return reverse('admin:auth_group_members', args=[group.pk])


def test_group_change_page_has_the_members_button(admin_client, group):
    response = admin_client.get(reverse('admin:auth_group_change', args=[group.pk]))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find('a', href=lambda href: href and href.startswith(_members_url(group))) is not None


def test_members_lists_the_users_of_the_group(admin_client, group):
    zed = UserFactory(username='zed', first_name='Zed', last_name='Last')
    anna = UserFactory(username='anna', first_name='Anna', last_name='Rossi')
    outsider = UserFactory(username='outsider')
    zed.groups.add(group)
    anna.groups.add(group)
    outsider.groups.add(Group.objects.create(name='Other'))

    response = admin_client.get(_members_url(group))

    assert response.status_code == 200
    rows = BeautifulSoup(response.content, 'html.parser').select('#group-members tbody tr')
    assert [[cell.get_text(strip=True) for cell in row.find_all('td')] for row in rows] == [
        ['anna', 'Anna', 'Rossi'],
        ['zed', 'Zed', 'Last'],
    ]
    # the username links to the user's admin page
    assert rows[0].find('a')['href'] == reverse('admin:core_user_change', args=[anna.pk])


def test_members_of_an_empty_group(admin_client, group):
    response = admin_client.get(_members_url(group))

    assert response.status_code == 200
    assert 'No users are assigned to this group.' in response.content.decode()


@pytest.mark.parametrize(
    ('permissions', 'expected_status'),
    [
        pytest.param([], 403, id='no-permission'),
        pytest.param(['view_group'], 200, id='view-group'),
    ],
)
def test_members_needs_access_to_groups(client, group, permissions, expected_status):
    staff = UserFactory(username='staff', password='pass123', is_staff=True)
    staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='auth', codename__in=permissions))
    client.login(username='staff', password='pass123')

    response = client.get(_members_url(group))

    assert response.status_code == expected_status
