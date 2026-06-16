from typing import Any

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
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
                regex=r'^[+\d\s-]+$', message='Phone number must contain only digits, +, spaces, or hyphens.'
            )
        ],
    )

    class Meta:
        model = PhoneInfo
        fields = ('number', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        ret = super().to_internal_value(data)
        if 'phone' in ret:
            ret['number'] = ret.pop('phone')['number']
        return ret


class WebsiteInfoSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='website.url')

    class Meta:
        model = WebsiteInfo
        fields = ('url',)

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        ret = super().to_internal_value(data)
        if 'website' in ret:
            ret['url'] = ret.pop('website')['url']
        return ret


class EmailInfoSerializer(serializers.ModelSerializer):
    address = serializers.EmailField(source='email.address')

    class Meta:
        model = EmailInfo
        fields = ('address', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        ret = super().to_internal_value(data)
        if 'email' in ret:
            ret['address'] = ret.pop('email')['address']
        return ret


class AddressInfoSerializer(serializers.ModelSerializer):
    address = serializers.CharField(source='address.address')

    class Meta:
        model = AddressInfo
        fields = ('address', 'kind')

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        ret = super().to_internal_value(data)
        if 'address' in ret:
            ret['address'] = ret.pop('address')['address']
        return ret


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
