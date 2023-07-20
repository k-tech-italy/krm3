from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'krm3.currencies'

    def ready(self):
        super().ready()

        from .api import serializers  # noqa
