from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'krm3.core'

    def ready(self) -> None:
        super().ready()

        from .api import serializers  # noqa
