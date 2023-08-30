from django.contrib.auth import get_user_model
from rest_framework import mixins

from krm3.core.models import City, Client, Country, Project
from krm3.utils.serializers import ModelDefaultSerializerMetaclass

User = get_user_model()


class GenericViewSet:
    pass


class UserSerializer(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):
    class Meta:
        model = User
        fields = '__all__'


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
