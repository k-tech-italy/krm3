from django.contrib.auth.models import Permission
from django.urls import reverse

from testutils.factories import ContactFactory


def test_admin_can_see_all_contacts(admin_client, admin_user):
    ContactFactory(user=admin_user)
    ContactFactory()
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 2

def test_user_with_perm_can_see_all_contacts(api_client, regular_user):
    ContactFactory(user=regular_user)
    ContactFactory()

    regular_user.user_permissions.add(Permission.objects.get(codename='view_contact'))

    response = api_client(regular_user).get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 2

def test_user_without_perm_can_see_only_his_own_contacts(api_client, regular_user):
    ContactFactory(user=regular_user)
    ContactFactory()

    response = api_client(regular_user).get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    assert response.json()['count'] == 1
    assert len(response.json()['results']) == 1

def test_response_structure_empty_m2m_fields(admin_client):
    contact = ContactFactory()
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    results = response.json()['results'][0]

    assert results['id'] == contact.id
    assert results['firstName'] == contact.first_name
    assert results['lastName'] == contact.last_name
    assert results['taxId'] == contact.tax_id
    assert results['jobTitle'] == contact.job_title

    results['phones'] = []
    results['websites'] = []
    results['emails'] = []
    results['addresses'] = []


def test_response_structure_with_m2m_fields(admin_client):

    contact = ContactFactory(phones=1, emails=2, addresses=3, websites=4)
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    results = response.json()['results'][0]

    assert len(results["phones"]) == contact.phones.count() == 1
    assert len(results["emails"]) == contact.emails.count() == 2
    assert len(results["addresses"]) == contact.addresses.count() == 3
    assert len(results["websites"]) == contact.websites.count() == 4

    for phone in contact.phones.all():
        assert phone.number in (phone['number'] for phone in results['phones'])

    for email in contact.emails.all():
        assert email.address in (email['address'] for email in results['emails'])

    for address in contact.addresses.all():
        assert address.address in (address['address'] for address in results['addresses'])

    for website in contact.websites.all():
        assert website.url in (website['url'] for website in results['websites'])
