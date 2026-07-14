import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from testutils.factories import ContactFactory

from krm3.core.models import Contact


def test_admin_can_see_all_contacts(admin_client, admin_user):
    ContactFactory(user=admin_user)
    ContactFactory()
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == status.HTTP_200_OK

    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 2


def test_user_with_perm_can_see_all_contacts(api_client, regular_user):
    ContactFactory(user=regular_user)
    ContactFactory()

    regular_user.user_permissions.add(Permission.objects.get(codename='view_contact'))

    response = api_client(regular_user).get(reverse('core-api:contacts-list'))

    assert response.status_code == status.HTTP_200_OK

    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 2


def test_user_without_perm_can_see_only_his_own_contacts(api_client, regular_user):
    ContactFactory(user=regular_user)
    ContactFactory()

    response = api_client(regular_user).get(reverse('core-api:contacts-list'))

    assert response.status_code == status.HTTP_200_OK

    assert response.json()['count'] == 1
    assert len(response.json()['results']) == 1


def test_response_structure_empty_m2m_fields(admin_client):
    contact = ContactFactory()
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == status.HTTP_200_OK

    results = response.json()['results'][0]

    assert results['id'] == contact.id
    assert results['firstName'] == contact.first_name
    assert results['lastName'] == contact.last_name
    assert results['taxId'] == contact.tax_id
    assert results['jobTitle'] == contact.job_title
    assert results['company']['name'] == contact.company.name
    assert results['company']['picture'] == contact.company.picture
    assert results['phones'] == []
    assert results['emails'] == []
    assert results['addresses'] == []
    assert results['websites'] == []


def test_response_structure_with_m2m_fields(admin_client):

    contact = ContactFactory(phones=1, emails=2, addresses=3, websites=4)
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == status.HTTP_200_OK

    results = response.json()['results'][0]

    assert len(results['phones']) == contact.phones.count() == 1
    assert len(results['emails']) == contact.emails.count() == 2
    assert len(results['addresses']) == contact.addresses.count() == 3
    assert len(results['websites']) == contact.websites.count() == 4

    for phone in contact.phones.all():
        assert phone.number in (phone['number'] for phone in results['phones'])

    for email in contact.emails.all():
        assert email.address in (email['address'] for email in results['emails'])

    for address in contact.addresses.all():
        assert address.address in (address['address'] for address in results['addresses'])

    for website in contact.websites.all():
        assert website.url in (website['url'] for website in results['websites'])


def test_can_filter_active_contacts(admin_client):
    ContactFactory(is_active=True)
    ContactFactory(is_active=False)

    response = admin_client.get(reverse('core-api:contacts-list'), {'active': 'true'})

    assert response.status_code == status.HTTP_200_OK

    assert response.json()['count'] == 1
    assert len(response.json()['results']) == 1
    assert response.json()['results'][0]['isActive'] is True


def test_create_contact(api_client, admin_user):
    response = api_client(admin_user).post(
        reverse('core-api:contacts-list'),
        data={
            'first_name': 'New',
            'last_name': 'Contact',
            'phones': [{'number': '+1234567890'}],
            'emails': [{'address': 'email@example.com'}],
            'addresses': [{'address': '123 Main St'}],
            'websites': [{'url': 'www.example.com'}],
        },
        content_type='application/json',
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data['firstName'] == 'New'
    assert data['lastName'] == 'Contact'
    assert data['phones'][0]['number'] == '+1234567890'
    assert data['emails'][0]['address'] == 'email@example.com'
    assert data['addresses'][0]['address'] == '123 Main St'
    assert data['websites'][0]['url'] == 'www.example.com'


@pytest.mark.parametrize(
    'payload, field',
    [
        pytest.param(
            {'first_name': '', 'last_name': 'Doe', 'phones': [], 'emails': []},
            'firstName',
            id='empty_first_name',
        ),
        pytest.param(
            {'first_name': 'John', 'last_name': '', 'phones': [], 'emails': []},
            'lastName',
            id='empty_last_name',
        ),
    ],
)
def test_create_contact_required_fields(payload, field, admin_client):
    response = admin_client.post(
        reverse('core-api:contacts-list'),
        data=payload,
        content_type='application/json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    errors = response.json()
    assert field in errors
    assert errors[field][0] == 'This field may not be blank.'


@pytest.mark.parametrize(
    'title, expected_status',
    [
        pytest.param(Contact.TitleChoices.DOCTOR, status.HTTP_201_CREATED, id='valid_doctor'),
        pytest.param(Contact.TitleChoices.MRS, status.HTTP_201_CREATED, id='valid_mrs'),
        pytest.param('invalid', status.HTTP_400_BAD_REQUEST, id='invalid_title'),
    ],
)
def test_create_contact_title_validation(title, expected_status, admin_client):
    response = admin_client.post(
        reverse('core-api:contacts-list'),
        data={'first_name': 'John', 'last_name': 'Doe', 'title': title, 'phones': [], 'emails': []},
        content_type='application/json',
    )
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    'phone_number, expected_status',
    [
        pytest.param('abc', status.HTTP_400_BAD_REQUEST, id='letters_only'),
        pytest.param('phone123', status.HTTP_400_BAD_REQUEST, id='letters_and_digits'),
        pytest.param('!@#$%', status.HTTP_400_BAD_REQUEST, id='special_chars'),
        pytest.param('+1234567890', status.HTTP_201_CREATED, id='plus_prefix'),
        pytest.param('1234567890', status.HTTP_201_CREATED, id='digits_only'),
        pytest.param('+1 234 567 890', status.HTTP_201_CREATED, id='with_spaces'),
        pytest.param('+1-234-567-890', status.HTTP_201_CREATED, id='with_dashes'),
        pytest.param('+1-234 567 890', status.HTTP_201_CREATED, id='with_dashes_spaces'),
        pytest.param('++++++++1-234 567 890', status.HTTP_400_BAD_REQUEST, id='too_many_pluses'),
        pytest.param('1 234 567 +890', status.HTTP_400_BAD_REQUEST, id='plus_prefix_in_between'),
        pytest.param('+', status.HTTP_400_BAD_REQUEST, id='plus_prefix_alone'),
    ],
)
def test_create_contact_phone_validation(phone_number, expected_status, admin_client):
    response = admin_client.post(
        reverse('core-api:contacts-list'),
        data={
            'first_name': 'John',
            'last_name': 'Doe',
            'phones': [{'number': phone_number}],
            'emails': [],
        },
        content_type='application/json',
    )
    assert response.status_code == expected_status


def test_titles_endpoint_returns_all_choices(admin_client):
    response = admin_client.get(reverse('core-api:titles-list'))
    assert response.status_code == status.HTTP_200_OK
    titles = response.json()
    expected = [{'value': choice.value, 'label': choice.label} for choice in Contact.TitleChoices]
    assert titles == expected


def test_patch_contact_deactivates(admin_client):
    contact = ContactFactory(is_active=True)
    response = admin_client.patch(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
        data={'isActive': False},
        content_type='application/json',
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['isActive'] is False
    contact.refresh_from_db()
    assert contact.is_active is False


def test_patch_contact_activates(admin_client):
    contact = ContactFactory(is_active=False)
    response = admin_client.patch(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
        data={'isActive': True},
        content_type='application/json',
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['isActive'] is True
    contact.refresh_from_db()
    assert contact.is_active is True


def test_delete_contact(admin_client):
    contact = ContactFactory()
    response = admin_client.delete(reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Contact.objects.filter(pk=contact.pk).exists()


def test_patch_contact_preserves_related_data(admin_client):
    contact = ContactFactory(phones=1, emails=1, addresses=1, websites=1, is_active=True)
    response = admin_client.patch(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
        data={'isActive': False},
        content_type='application/json',
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['isActive'] is False
    contact.refresh_from_db()
    assert contact.is_active is False
    assert contact.phones.count() == 1
    assert contact.emails.count() == 1
    assert contact.addresses.count() == 1
    assert contact.websites.count() == 1


def test_patch_contact_updates_related_data(admin_client):
    contact = ContactFactory(phones=2, emails=2, addresses=2, websites=2)

    phone = contact.phones.first()
    email = contact.emails.first()
    address = contact.addresses.first()
    website = contact.websites.first()

    response = admin_client.patch(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
        data={
            'phones': [
                {'number': phone.number, 'kind': 'updated'},
                {'number': '+000000000', 'kind': 'new'},
            ],
            'emails': [
                {'address': email.address, 'kind': 'updated'},
                {'address': 'new@example.com', 'kind': 'new'},
            ],
            'addresses': [
                {'address': address.address, 'kind': 'updated'},
                {'address': 'New Address', 'kind': 'new'},
            ],
            'websites': [
                {'url': website.url},
                {'url': 'https://new.example.com'},
            ],
        },
        content_type='application/json',
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['firstName'] == contact.first_name

    assert len(data['phones']) == 2
    assert len(data['emails']) == 2
    assert len(data['addresses']) == 2
    assert len(data['websites']) == 2


@pytest.mark.parametrize(
    ('permission', 'expected'),
    [
        pytest.param('add_contact', status.HTTP_201_CREATED, id='user_with_perm_create'),
        pytest.param(None, status.HTTP_403_FORBIDDEN, id='user_without_perm_create'),
    ],
)
def test_create_contact_permissions(permission, expected, regular_user, api_client):
    if permission:
        regular_user.user_permissions.add(Permission.objects.get(codename=permission))

    response = api_client(regular_user).get(reverse('core-api:contacts-list'))
    response = api_client(regular_user).post(
        reverse('core-api:contacts-list'),
        data={'first_name': 'John', 'last_name': 'Doe', 'phones': [], 'emails': []},
        content_type='application/json',
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    ('permission', 'expected'),
    [
        pytest.param('change_contact', status.HTTP_200_OK, id='user_with_perm_change'),
        pytest.param(None, status.HTTP_403_FORBIDDEN, id='user_without_perm_change'),
    ],
)
def test_edit_contact_permissions(permission, expected, regular_user, api_client):
    if permission:
        regular_user.user_permissions.add(Permission.objects.get(codename=permission))

    contact = ContactFactory(user=regular_user)
    response = api_client(regular_user).patch(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
        data={'jobTitle': 'Updated'},
        content_type='application/json',
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    ('permission', 'expected'),
    [
        pytest.param('delete_contact', status.HTTP_204_NO_CONTENT, id='user_with_perm_delete'),
        pytest.param(None, status.HTTP_403_FORBIDDEN, id='user_without_perm_delete'),
    ],
)
def test_delete_contact_permissions(permission, expected, regular_user, api_client):
    if permission:
        regular_user.user_permissions.add(Permission.objects.get(codename=permission))

    contact = ContactFactory(user=regular_user)
    response = api_client(regular_user).delete(
        reverse('core-api:contacts-detail', kwargs={'pk': contact.pk}),
    )
    assert response.status_code == expected
