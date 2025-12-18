from django.contrib.auth import get_user_model

from krm3.core.models import City, Client, Country, Project, Contact, PhoneInfo, WebsiteInfo, EmailInfo, \
    AddressInfo
from krm3.utils.serializers import ModelDefaultSerializerMetaclass
from rest_framework import serializers

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
    number = serializers.CharField(source='phone.number')

    class Meta:
        model = PhoneInfo
        fields = ('number', 'kind')

class WebsiteInfoSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='website.url')

    class Meta:
        model = WebsiteInfo
        fields = ('url',)

class EmailInfoSerializer(serializers.ModelSerializer):
    address = serializers.CharField(source='email.address')

    class Meta:
        model = EmailInfo
        fields = ('address', 'kind')

class AddressInfoSerializer(serializers.ModelSerializer):
    address = serializers.CharField(source='address.address')
    class Meta:
        model = AddressInfo
        fields = ('address', 'kind')

class ContactSerializer(metaclass=ModelDefaultSerializerMetaclass):
    phones = PhoneInfoSerializer(many=True, read_only=True, source='phoneinfo_set')
    websites = WebsiteInfoSerializer(many=True, read_only=True, source='websiteinfo_set')
    emails = EmailInfoSerializer(many=True, read_only=True, source='emailinfo_set')
    addresses = AddressInfoSerializer(many=True, read_only=True, source='addressinfo_set')
    class Meta:
        model = Contact
        fields = '__all__'
        depth = 2
