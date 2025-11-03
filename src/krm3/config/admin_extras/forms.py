"""Admin extras forms module."""

from django import forms
from django.conf import settings


class SentryForm(forms.Form):  # noqa: D101
    ACTIONS = [
        ('capture_event', 'capture_event()'),
        ('capture_exception', 'capture_exception'),
        ('capture_message', 'capture_message'),
        ('logging_integration', 'logging_integration'),
        ('404', 'Error 404'),
        ('500', 'Error 500'),
    ]

    action = forms.ChoiceField(choices=ACTIONS, widget=forms.RadioSelect)


class RedisCLIForm(forms.Form):  # noqa: D101
    command = forms.CharField()
    connection = forms.ChoiceField(choices=zip(settings.CACHES.keys(), settings.CACHES.keys(), strict=False))
