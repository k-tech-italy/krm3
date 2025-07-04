from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'krm3.core'

    def ready(self) -> None:
        super().ready()

        from .api import serializers  # noqa
