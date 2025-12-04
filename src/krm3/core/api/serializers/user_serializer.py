from typing import Any

from flags.state import flag_enabled
from flags.sources import get_flags
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from krm3.config.environ import env
from krm3.core.models import Resource, UserProfile
from krm3.core.models.auth import User
from krm3.utils.serializers import ModelDefaultSerializerMetaclass

LABEL_TO_FLAG_URL_MAP = [
    {
        'flag': 'TRASFERTE_ENABLED',
        'url': 'trasferte',
        'label': 'Missions',
    },
    {
        'flag': 'TIMESHEET_ENABLED',
        'url': 'timesheet',
        'label': 'Timesheet',
    },
    {
        'flag': 'REPORT_ENABLED',
        'url': 'be/',
        'label': 'Report',
    }
]



# XXX: why is this not a BaseSerializer? The metaclass implicitly
#      setting the base class in __new__() is making the type checker
#      go insane
class UserResourceSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Resource
        fields = '__all__'


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


# XXX: why is this not a BaseSerializer? The metaclass implicitly
#      setting the base class in __new__() is making the type checker
#      go insane
class UserSerializer(metaclass=ModelDefaultSerializerMetaclass):
    profile = ProfileSerializer(required=False, read_only=True, allow_null=True)
    # XXX: since this is NOT a serializer according to the type checker,
    #      all the kwargs passed to __init__() are flagged as unknown
    resource = UserResourceSerializer(required=False, read_only=True, allow_null=True)
    permissions = SerializerMethodField()
    flags = SerializerMethodField()
    config = SerializerMethodField()

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
            'permissions',
            'flags',
            'config',
        )

    def get_config(self, *args) -> dict[str, Any]:
        """Return a dictionary of configuration values."""
        config = {
            'modules': [
                obj
                for obj in LABEL_TO_FLAG_URL_MAP
                if flag_enabled(obj['flag'], request=self.context['request'])  # type: ignore
            ]
        }

        default = env('DEFAULT_MODULE')
        if default and default in config['modules']:
            config['default_module'] = default

        return config

    def get_permissions(self, obj: User) -> list[str] | None:
        """Return the permissions of the user, or None if the user is a superuser."""
        return None if obj.is_superuser else sorted(obj.get_all_permissions())

    def get_flags(self, *args) -> dict[str, bool] | None:
        """Return a dictionary of feature flags and their enabled status."""
        return {
            key: flag_enabled(key, request=self.context['request'])  # type: ignore
            for key in list(get_flags().keys())
        }


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
        depth = 0
