from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'krm3.core'

    def ready(self):
        super().ready()

        import krm3.patching  # noqa

        from .api import serializers  # noqa
