from django.contrib.auth import get_user_model
from rest_framework import mixins
from rest_framework.serializers import ModelSerializer

from krm3.core.models import City, Client, Country, Project, UserProfile
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


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('picture',)


class CitySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = City
        fields = '__all__'


class CountrySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Country
        fields = '__all__'
