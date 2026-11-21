import pytest
from django.urls import reverse
from testutils.factories import UserFactory

from krm3.core.models import SavedFilter

LIST_URL = 'core-api:saved-filter-list'


def _detail_url(saved_filter: SavedFilter) -> str:
    return reverse('core-api:saved-filter-detail', args=[saved_filter.pk])


@pytest.mark.django_db
def test_list_returns_only_own_filters(api_client, regular_user):
    own = SavedFilter.objects.create(user=regular_user, page='missions', name='Mine', values={'status': ['DRAFT']})
    SavedFilter.objects.create(user=UserFactory(), page='missions', name='Theirs')

    response = api_client(user=regular_user).get(reverse(LIST_URL))

    assert response.status_code == 200
    assert [item['id'] for item in response.data] == [own.pk]


@pytest.mark.django_db
def test_list_can_be_limited_to_one_page(api_client, regular_user):
    SavedFilter.objects.create(user=regular_user, page='missions', name='Missions filter')
    expenses = SavedFilter.objects.create(user=regular_user, page='expenses', name='Expenses filter')

    response = api_client(user=regular_user).get(reverse(LIST_URL), {'page': 'expenses'})

    assert [item['id'] for item in response.data] == [expenses.pk]


@pytest.mark.django_db
def test_superuser_lists_only_own_filters(api_client, admin_user, regular_user):
    SavedFilter.objects.create(user=regular_user, page='missions', name='Not for the admin')

    response = api_client(user=admin_user).get(reverse(LIST_URL))

    assert response.data == []


@pytest.mark.django_db
def test_create_saves_the_filter_for_the_logged_in_user(api_client, regular_user):
    payload = {
        'page': 'missions',
        'name': 'Drafts of 2025',
        'values': {'status': ['DRAFT'], 'dateFrom': '2025-01-01'},
        'summary': 'Status: Draft; From: 2025-01-01',
        'url': '/trasferte?status=DRAFT&dateFrom=2025-01-01',
    }

    response = api_client(user=regular_user).post(reverse(LIST_URL), payload, format='json')

    assert response.status_code == 201
    saved = SavedFilter.objects.get(user=regular_user)
    assert saved.name == 'Drafts of 2025'
    assert saved.summary == payload['summary']
    assert saved.url == payload['url']
    # the camelCase keys of the frontend come back as they were sent
    assert response.json()['values'] == payload['values']


@pytest.mark.django_db
def test_create_with_an_existing_name_replaces_the_filter(api_client, regular_user):
    existing = SavedFilter.objects.create(user=regular_user, page='missions', name='Mine', values={'status': ['DRAFT']})

    response = api_client(user=regular_user).post(
        reverse(LIST_URL), {'page': 'missions', 'name': 'Mine', 'values': {'year': '2025'}}, format='json'
    )

    assert response.status_code == 200
    existing.refresh_from_db()
    assert existing.values == {'year': '2025'}
    assert SavedFilter.objects.filter(user=regular_user).count() == 1


@pytest.mark.django_db
def test_create_with_the_name_of_another_user_filter_creates_a_new_one(api_client, regular_user):
    other = SavedFilter.objects.create(user=UserFactory(), page='missions', name='Shared name', values={'year': '2024'})

    response = api_client(user=regular_user).post(
        reverse(LIST_URL), {'page': 'missions', 'name': 'Shared name', 'values': {'year': '2025'}}, format='json'
    )

    assert response.status_code == 201
    other.refresh_from_db()
    assert other.values == {'year': '2024'}


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param({'name': 'No page', 'values': {}}, id='missing-page'),
        pytest.param({'page': 'missions', 'values': {}}, id='missing-name'),
        pytest.param({'page': 'missions', 'name': '', 'values': {}}, id='blank-name'),
        pytest.param({'page': 'missions', 'name': 'List', 'values': ['DRAFT']}, id='values-not-a-mapping'),
        pytest.param({'page': 'missions', 'name': 'Number', 'values': {'year': 2025}}, id='value-not-a-string'),
        pytest.param({'page': 'missions', 'name': 'Nested', 'values': {'status': [['DRAFT']]}}, id='nested-list'),
    ],
)
@pytest.mark.django_db
def test_create_rejects_invalid_data(api_client, regular_user, payload):
    response = api_client(user=regular_user).post(reverse(LIST_URL), payload, format='json')

    assert response.status_code == 400
    assert not SavedFilter.objects.exists()


@pytest.mark.django_db
def test_delete_own_filter(api_client, regular_user):
    saved = SavedFilter.objects.create(user=regular_user, page='missions', name='Mine')

    response = api_client(user=regular_user).delete(_detail_url(saved))

    assert response.status_code == 204
    assert not SavedFilter.objects.exists()


@pytest.mark.django_db
def test_cannot_delete_the_filter_of_another_user(api_client, regular_user):
    saved = SavedFilter.objects.create(user=UserFactory(), page='missions', name='Theirs')

    response = api_client(user=regular_user).delete(_detail_url(saved))

    assert response.status_code == 404
    assert SavedFilter.objects.filter(pk=saved.pk).exists()


@pytest.mark.parametrize('method', [pytest.param('get', id='list'), pytest.param('post', id='create')])
@pytest.mark.django_db
def test_saved_filters_require_authentication(api_client, method):
    response = getattr(api_client(), method)(reverse(LIST_URL), {}, format='json')

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_saving_a_default_filter_makes_it_the_only_default_of_the_page(api_client, regular_user):
    previous = SavedFilter.objects.create(user=regular_user, page='missions', name='Old default', is_default=True)
    other_page = SavedFilter.objects.create(user=regular_user, page='expenses', name='Expenses', is_default=True)
    other_user = SavedFilter.objects.create(user=UserFactory(), page='missions', name='Theirs', is_default=True)

    response = api_client(user=regular_user).post(
        reverse(LIST_URL), {'page': 'missions', 'name': 'New default', 'values': {}, 'isDefault': True}, format='json'
    )

    assert response.status_code == 201
    assert response.json()['isDefault'] is True
    previous.refresh_from_db()
    other_page.refresh_from_db()
    other_user.refresh_from_db()
    assert previous.is_default is False
    assert other_page.is_default is True
    assert other_user.is_default is True


@pytest.mark.parametrize(
    ('is_default', 'expected'),
    [
        pytest.param(True, True, id='still-default'),
        pytest.param(False, False, id='no-longer-default'),
    ],
)
@pytest.mark.django_db
def test_replacing_a_filter_sets_its_default_flag(api_client, regular_user, is_default, expected):
    saved = SavedFilter.objects.create(user=regular_user, page='missions', name='Mine', is_default=True)

    response = api_client(user=regular_user).post(
        reverse(LIST_URL), {'page': 'missions', 'name': 'Mine', 'values': {}, 'isDefault': is_default}, format='json'
    )

    assert response.status_code == 200
    saved.refresh_from_db()
    assert saved.is_default is expected


@pytest.mark.django_db
def test_filters_are_not_default_unless_requested(api_client, regular_user):
    api_client(user=regular_user).post(reverse(LIST_URL), {'page': 'missions', 'name': 'Mine'}, format='json')

    assert SavedFilter.objects.get(user=regular_user).is_default is False


@pytest.mark.django_db
def test_database_allows_only_one_default_per_user_and_page(regular_user):
    from django.db import IntegrityError, transaction  # noqa: PLC0415

    SavedFilter.objects.create(user=regular_user, page='missions', name='First', is_default=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        SavedFilter.objects.create(user=regular_user, page='missions', name='Second', is_default=True)
