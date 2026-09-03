from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'krm3.currencies'

    def ready(self) -> None:
        super().ready()

        from .api import serializers  # noqa
