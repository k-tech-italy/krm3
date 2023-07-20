from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'krm3.core'

    def ready(self):
        super().ready()

        from .api import serializers  # noqa
