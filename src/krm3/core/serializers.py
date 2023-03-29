from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer

from krm3.core.models import UserProfile

User = get_user_model()


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('picture',)


class UserSerializer(ModelSerializer):
    profile = ProfileSerializer(required=False, read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_superuser', 'is_staff', 'is_active', 'last_login', 'profile')
