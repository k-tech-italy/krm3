from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer

from krm3.core.models import Resource, UserProfile
from krm3.utils.serializers import ModelDefaultSerializerMetaclass

User = get_user_model()


class ResourceSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Resource
        fields = '__all__'


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class UserSerializer(metaclass=ModelDefaultSerializerMetaclass):
    profile = ProfileSerializer(required=False, read_only=True, allow_null=True)
    resource = ResourceSerializer(required=False, read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_superuser',
            'is_staff',
            'is_active',
            'last_login',
            'resource',
            'profile',
        )
