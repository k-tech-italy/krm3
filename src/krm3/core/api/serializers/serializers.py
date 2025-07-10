from django.contrib.auth import get_user_model

from krm3.core.models import City, Client, Country, Project
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
