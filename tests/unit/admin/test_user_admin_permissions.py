import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from testutils.factories import UserFactory


def _perm(codename: str) -> Permission:
    return Permission.objects.get(content_type__app_label='core', codename=codename)


def _permissions_url(user) -> str:
    return reverse('admin:core_user_permissions', args=[user.pk])


def _items(response) -> list:
    return BeautifulSoup(response.content, 'html.parser').select('#permissions-list li')


@pytest.fixture
def member():
    user = UserFactory(username='member')
    accounting = Group.objects.create(name='Accounting')
    managers = Group.objects.create(name='Managers')
    accounting.permissions.add(_perm('view_mission'), _perm('view_expense'))
    managers.permissions.add(_perm('view_mission'))
    user.groups.add(accounting, managers)
    user.user_permissions.add(_perm('add_mission'), _perm('view_expense'))
    # a group the user is not in does not count
    Group.objects.create(name='Other').permissions.add(_perm('delete_mission'))
    return user


def test_user_change_page_has_the_permissions_button(admin_client, member):
    response = admin_client.get(reverse('admin:core_user_change', args=[member.pk]))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find('a', href=lambda href: href and href.startswith(_permissions_url(member))) is not None


def test_permissions_lists_each_permission_with_the_groups_that_give_it(admin_client, member):
    response = admin_client.get(_permissions_url(member))

    assert response.status_code == 200
    texts = {item.find('a').get_text(strip=True): ' '.join(item.get_text().split()) for item in _items(response)}
    assert texts == {
        'Can add mission': 'Can add mission (assigned directly)',
        'Can view expense': 'Can view expense (assigned directly, Accounting)',
        'Can view mission': 'Can view mission (Accounting, Managers)',
    }


def test_permission_name_links_to_the_permission(admin_client, member):
    response = admin_client.get(_permissions_url(member))

    link = next(item.find('a') for item in _items(response) if 'Can view mission' in item.get_text())
    assert link['href'] == reverse('admin:auth_permission_change', args=[_perm('view_mission').pk])
    assert link['title'] == 'core.view_mission'


def test_permissions_of_an_inactive_user_are_listed_with_a_note(admin_client, member):
    member.is_active = False
    member.save()

    response = admin_client.get(_permissions_url(member))

    assert len(_items(response)) == 3
    assert 'This user is not active' in response.content.decode()


def test_superuser_gets_a_note(admin_client):
    superuser = UserFactory(username='boss', is_superuser=True)

    response = admin_client.get(_permissions_url(superuser))

    content = response.content.decode()
    assert 'This user is a superuser and has every permission' in content
    assert 'No permissions are assigned to this user' in content


def test_user_without_permissions(admin_client):
    response = admin_client.get(_permissions_url(UserFactory()))

    assert response.status_code == 200
    assert _items(response) == []
    assert 'No permissions are assigned to this user, directly or through a group.' in response.content.decode()


def test_no_permission_is_needed_to_open_the_list(client, member):
    UserFactory(username='staff', password='pass123', is_staff=True)
    client.login(username='staff', password='pass123')

    response = client.get(_permissions_url(member))

    assert response.status_code == 200
    assert len(_items(response)) == 3


def test_permissions_are_sorted_by_name(admin_client):
    user = UserFactory()
    user.user_permissions.add(_perm('view_mission'), _perm('add_expense'), _perm('change_contract'))

    response = admin_client.get(_permissions_url(user))

    assert [item.find('a').get_text(strip=True) for item in _items(response)] == [
        'Can add expense',
        'Can change contract',
        'Can view mission',
    ]


def test_each_entry_can_be_found_by_permission_or_group_name(admin_client, member):
    response = admin_client.get(_permissions_url(member))

    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.find('input', {'id': 'permissions-search', 'type': 'search'}) is not None
    search_texts = {item.find('a').get_text(strip=True): item['data-search'] for item in _items(response)}
    assert search_texts['Can view mission'] == 'can view mission core.view_mission accounting managers'
    assert search_texts['Can add mission'] == 'can add mission core.add_mission '


def test_no_search_bar_without_permissions(admin_client):
    response = admin_client.get(_permissions_url(UserFactory()))

    assert BeautifulSoup(response.content, 'html.parser').find('input', {'id': 'permissions-search'}) is None
