from django.apps import AppConfig as BaseAppConfig

class AppConfig(BaseAppConfig):
    name = 'krm3.core'

    def ready(self) -> None:
        super().ready()

        from . import flags as _  # noqa
        from .api import serializers as _  # noqa
