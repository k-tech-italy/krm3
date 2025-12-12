from django.urls import reverse

from testutils.factories import ContactFactory


def test_admin_should_be_able_to_get_all_contacts(admin_client):
    contact_1 = ContactFactory(phones=2, emails=2, addresses=2, social_media_urls=2)
    contact_2 =  ContactFactory(phones=2, emails=2, addresses=2, social_media_urls=2)
    response = admin_client.get(reverse('core-api:contacts-list'))

    assert response.status_code == 200

    results_1 = response.json()['results'][0]
    assert response.json()['count'] == 2
    assert len(response.json()['results']) == 2
    assert results_1['id'] == contact_1.id
    assert results_1['firstName'] == contact_1.first_name
    assert results_1['lastName'] == contact_1.last_name
    assert results_1['taxId'] == contact_1.tax_id
    assert results_1['jobTitle'] == contact_1.job_title
    contact_1.phones.get(number=results_1['phones'][0]['number'])
    contact_1.phones.get(number=results_1['phones'][1]['number'])
    contact_1.social_media_urls.get(url=results_1['socialMediaUrls'][0]['url'])
    contact_1.social_media_urls.get(url=results_1['socialMediaUrls'][1]['url'])
    contact_1.emails.get(address=results_1['emails'][0]['address'])
    contact_1.emails.get(address=results_1['emails'][1]['address'])
    contact_1.addresses.get(address=results_1['addresses'][0]['address'])
    contact_1.addresses.get(address=results_1['addresses'][1]['address'])

    results_2 = response.json()['results'][1]
    assert results_2['id'] == contact_2.id
    assert results_2['firstName'] == contact_2.first_name
    assert results_2['lastName'] == contact_2.last_name
    assert results_2['taxId'] == contact_2.tax_id
    assert results_2['jobTitle'] == contact_2.job_title
    contact_2.phones.get(number=results_2['phones'][0]['number'])
    contact_2.phones.get(number=results_2['phones'][1]['number'])
    contact_2.social_media_urls.get(url=results_2['socialMediaUrls'][0]['url'])
    contact_2.social_media_urls.get(url=results_2['socialMediaUrls'][1]['url'])
    contact_2.emails.get(address=results_2['emails'][0]['address'])
    contact_2.emails.get(address=results_2['emails'][1]['address'])
    contact_2.addresses.get(address=results_2['addresses'][0]['address'])
    contact_2.addresses.get(address=results_2['addresses'][1]['address'])

def test_user_should_be_able_to_see_only_his_contact(client, regular_user):
    client.force_login(regular_user)
    assigned_contact = ContactFactory(phones=2, emails=2, addresses=2, social_media_urls=2, user=regular_user)
    not_assigned_contact = ContactFactory(phones=2, emails=2, addresses=2, social_media_urls=2)

    response = client.get(reverse('core-api:contacts-list'))

    assert response.status_code == 200
    assert response.json()['count'] == 1
    assert len(response.json()['results']) == 1
    assert response.json()['results'][0]['id'] == assigned_contact.id
    assert assigned_contact.emails.first().address in response.content.decode()
    assert not_assigned_contact.emails.first().address not in response.content.decode()
