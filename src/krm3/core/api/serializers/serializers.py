from typing import Any

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import transaction
from rest_framework import serializers

from krm3.core.models import (
    Address,
    AddressInfo,
    City,
    Client,
    Contact,
    Country,
    Email,
    EmailInfo,
    Phone,
    PhoneInfo,
    Project,
    Website,
    WebsiteInfo,
)
from krm3.utils.serializers import ModelDefaultSerializerMetaclass

User = get_user_model()


class GenericViewSet:
    pass


class ClientSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Client
        fields = '__all__'


class ProjectSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Project
        fields = '__all__'


class CitySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = City
        fields = '__all__'


class CountrySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Country
        fields = '__all__'


class PhoneInfoSerializer(serializers.ModelSerializer):
    number = serializers.CharField(
        source='phone.number',
        validators=[
            RegexValidator(
                regex=r'^\+?\d[\d\s-]*$',
                message='Phone number must start with a digit and can contain only digits, spaces, or hyphens. \
                Optional + sign allowed only at the start.',
            )
        ],
    )

    class Meta:
        model = PhoneInfo
        fields = ('number', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        value = super().to_internal_value(data)
        if 'phone' in value:
            value['number'] = value.pop('phone')['number']
        return value


class WebsiteInfoSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='website.url')

    class Meta:
        model = WebsiteInfo
        fields = ('url',)

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        value = super().to_internal_value(data)
        if 'website' in value:
            value['url'] = value.pop('website')['url']
        return value


class EmailInfoSerializer(serializers.ModelSerializer):
    address = serializers.EmailField(source='email.address')

    class Meta:
        model = EmailInfo
        fields = ('address', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        value = super().to_internal_value(data)
        if 'email' in value:
            value['address'] = value.pop('email')['address']
        return value


class AddressInfoSerializer(serializers.ModelSerializer):
    address = serializers.CharField(source='address.address')

    class Meta:
        model = AddressInfo
        fields = ('address', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        value = super().to_internal_value(data)
        if 'address' in value:
            value['address'] = value.pop('address')['address']
        return value


class ContactSerializer(metaclass=ModelDefaultSerializerMetaclass):
    phones = PhoneInfoSerializer(many=True, source='phoneinfo_set')
    websites = WebsiteInfoSerializer(many=True, source='websiteinfo_set', required=False, allow_empty=True)
    emails = EmailInfoSerializer(many=True, source='emailinfo_set')
    addresses = AddressInfoSerializer(many=True, source='addressinfo_set', required=False, allow_empty=True)

    class Meta:
        model = Contact
        fields = '__all__'
        depth = 2

    def create(self, validated_data: dict[str, Any]) -> Contact:
        phones_data = validated_data.pop('phoneinfo_set', [])
        emails_data = validated_data.pop('emailinfo_set', [])
        websites_data = validated_data.pop('websiteinfo_set', [])
        addresses_data = validated_data.pop('addressinfo_set', [])

        with transaction.atomic():
            contact = Contact.objects.create(**validated_data)

            for phone in phones_data:
                phone_obj, _ = Phone.objects.get_or_create(number=phone['number'])
                PhoneInfo.objects.create(contact=contact, phone=phone_obj, kind=phone.get('kind'))
            for email in emails_data:
                email_obj, _ = Email.objects.get_or_create(address=email['address'])
                EmailInfo.objects.create(contact=contact, email=email_obj, kind=email.get('kind'))
            for website in websites_data:
                website_obj, _ = Website.objects.get_or_create(url=website['url'])
                WebsiteInfo.objects.create(contact=contact, website=website_obj)
            for address in addresses_data:
                address_obj, _ = Address.objects.get_or_create(address=address['address'])
                AddressInfo.objects.create(contact=contact, address=address_obj, kind=address.get('kind'))

        return contact

    def update(self, instance: Contact, validated_data: dict[str, Any]) -> Contact:
        phones_data = validated_data.pop('phoneinfo_set', None)
        emails_data = validated_data.pop('emailinfo_set', None)
        websites_data = validated_data.pop('websiteinfo_set', None)
        addresses_data = validated_data.pop('addressinfo_set', None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if phones_data is not None:
                self._update_related_phones(instance, phones_data)
            if emails_data is not None:
                self._update_related_emails(instance, emails_data)
            if websites_data is not None:
                self._update_related_websites(instance, websites_data)
            if addresses_data is not None:
                self._update_related_addresses(instance, addresses_data)

        return instance

    def _update_related_phones(self, contact: Contact, phones_data: list[dict[str, Any]]) -> None:
        existing = {phone_info.phone.number: phone_info for phone_info in contact.phoneinfo_set.all()}
        submitted = {phone['number']: phone for phone in phones_data}

        for number, phone_info in existing.items():
            if number not in submitted:
                phone_info.delete()

        for number, phone in submitted.items():
            if number in existing:
                existing[number].kind = phone.get('kind')
                existing[number].save()
            else:
                phone_obj, _ = Phone.objects.get_or_create(number=number)
                PhoneInfo.objects.create(contact=contact, phone=phone_obj, kind=phone.get('kind'))

    def _update_related_emails(self, contact: Contact, emails_data: list[dict[str, Any]]) -> None:
        existing = {email_info.email.address: email_info for email_info in contact.emailinfo_set.all()}
        submitted = {email['address']: email for email in emails_data}

        for address, email_info in existing.items():
            if address not in submitted:
                email_info.delete()

        for address, email in submitted.items():
            if address in existing:
                existing[address].kind = email.get('kind')
                existing[address].save()
            else:
                email_obj, _ = Email.objects.get_or_create(address=address)
                EmailInfo.objects.create(contact=contact, email=email_obj, kind=email.get('kind'))

    def _update_related_websites(self, contact: Contact, websites_data: list[dict[str, Any]]) -> None:
        existing = {website_info.website.url: website_info for website_info in contact.websiteinfo_set.all()}
        submitted = {website['url']: website for website in websites_data}

        for url, website_info in existing.items():
            if url not in submitted:
                website_info.delete()

        for url in submitted:
            if url in existing:
                pass
            else:
                website_obj, _ = Website.objects.get_or_create(url=url)
                WebsiteInfo.objects.create(contact=contact, website=website_obj)

    def _update_related_addresses(self, contact: Contact, addresses_data: list[dict[str, Any]]) -> None:
        existing = {address_info.address.address: address_info for address_info in contact.addressinfo_set.all()}
        submitted = {address['address']: address for address in addresses_data}

        for address_str, address_info in existing.items():
            if address_str not in submitted:
                address_info.delete()

        for address_str, address in submitted.items():
            if address_str in existing:
                existing[address_str].kind = address.get('kind')
                existing[address_str].save()
            else:
                address_obj, _ = Address.objects.get_or_create(address=address_str)
                AddressInfo.objects.create(contact=contact, address=address_obj, kind=address.get('kind'))
