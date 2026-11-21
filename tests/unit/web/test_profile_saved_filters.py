import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from testutils.factories import UserFactory

from krm3.core.models import SavedFilter


@pytest.fixture
def user(client):
    user = UserFactory(username='owner', password='pass123')
    client.login(username='owner', password='pass123')
    return user


def _saved_filters_section(response):
    return BeautifulSoup(response.content, 'html.parser').find(attrs={'data-testid': 'saved-filters'})


def test_filters_tab_lists_own_filters_grouped_by_page(client, user):
    SavedFilter.objects.create(
        user=user,
        page='missions',
        name='Drafts',
        summary='Status: Draft',
        url='/trasferte?status=DRAFT',
        is_default=True,
    )
    SavedFilter.objects.create(user=user, page='expenses', name='This year', values={'year': '2025'})
    SavedFilter.objects.create(user=UserFactory(), page='missions', name='Not mine')

    response = client.get(reverse('user_profile', args=[user.pk]), {'tab': 'filters'})

    assert response.status_code == 200
    section = _saved_filters_section(response)
    assert section is not None
    groups = {group.find('h2').get_text(strip=True): group for group in section.select('.saved-filter-group')}
    assert list(groups) == ['Expenses', 'Missions']
    missions = groups['Missions'].get_text(' ', strip=True)
    assert 'Drafts' in missions
    assert 'Status: Draft' in missions
    assert 'Not mine' not in section.get_text()
    assert groups['Missions'].find('a', href='/trasferte?status=DRAFT') is not None
    assert groups['Missions'].select_one('.saved-filter-default').get_text(strip=True) == 'Default'
    assert groups['Expenses'].select_one('.saved-filter-default') is None
    # without a summary the raw values are shown
    assert 'year: 2025' in groups['Expenses'].get_text(' ', strip=True)


def test_filters_tab_without_filters_says_so(client, user):
    response = client.get(reverse('user_profile', args=[user.pk]), {'tab': 'filters'})

    assert 'You have no saved filters' in _saved_filters_section(response).get_text()


def test_profile_tab_is_the_default(client, user):
    response = client.get(reverse('user_profile', args=[user.pk]))

    assert _saved_filters_section(response) is None
    assert BeautifulSoup(response.content, 'html.parser').find('form', {'class': 'profile-form'}) is not None


def test_other_user_profile_does_not_show_their_filters(client, user):
    other = UserFactory()
    SavedFilter.objects.create(user=other, page='missions', name='Private')

    response = client.get(reverse('user_profile', args=[other.pk]), {'tab': 'filters'})

    assert response.status_code == 200
    assert _saved_filters_section(response) is None
    assert 'Private' not in response.content.decode()


def test_delete_own_filter_returns_to_the_filters_tab(client, user):
    saved = SavedFilter.objects.create(user=user, page='missions', name='Drafts')

    response = client.post(reverse('saved_filter_delete', args=[saved.pk]))

    assert response.status_code == 302
    assert response['Location'] == f'{reverse("user_profile", args=[user.pk])}?tab=filters'
    assert not SavedFilter.objects.exists()


def test_cannot_delete_the_filter_of_another_user(client, user):
    saved = SavedFilter.objects.create(user=UserFactory(), page='missions', name='Theirs')

    response = client.post(reverse('saved_filter_delete', args=[saved.pk]))

    assert response.status_code == 404
    assert SavedFilter.objects.filter(pk=saved.pk).exists()


def test_delete_requires_post(client, user):
    saved = SavedFilter.objects.create(user=user, page='missions', name='Drafts')

    response = client.get(reverse('saved_filter_delete', args=[saved.pk]))

    assert response.status_code == 405
    assert SavedFilter.objects.filter(pk=saved.pk).exists()


@pytest.mark.django_db
def test_delete_requires_login(client):
    saved = SavedFilter.objects.create(user=UserFactory(), page='missions', name='Drafts')

    response = client.post(reverse('saved_filter_delete', args=[saved.pk]))

    assert response.status_code == 302
    assert SavedFilter.objects.filter(pk=saved.pk).exists()
