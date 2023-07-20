from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer

from krm3.core.models import City, Client, Country, Project, Resource, UserProfile
from krm3.utils.serializers import ModelDefaultSerializerMetaclass

User = get_user_model()


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


class UserSerializer(metaclass=ModelDefaultSerializerMetaclass):
    profile = ProfileSerializer(required=False, read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_superuser', 'is_staff', 'is_active', 'last_login', 'profile')


class CitySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = City
        fields = '__all__'


class CountrySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Country
        fields = '__all__'


class ResourceSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Resource
        fields = '__all__'
