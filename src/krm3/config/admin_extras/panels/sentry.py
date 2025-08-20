"""Sentry admin panel module."""
import logging

import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.utils.html import urlize
from django.utils.html import format_html

from krm3.config.admin_extras.forms import SentryForm
from krm3.utils.sentry import get_sentry_dashboard, get_sentry_host

logger = logging.getLogger(__name__)


def sentry(self, request, extra_context=None):  # noqa: D103
    context = self.each_context(request)
    context['title'] = 'Sentry'
    context['info'] = {
        'SENTRY_DSN': settings.SENTRY_DSN,
        'SENTRY_SERVER_URL': format_html(urlize(get_sentry_host())),
        'SENTRY_DASHBOARD': format_html(urlize(get_sentry_dashboard())),
        'SENTRY_PROJECT': settings.SENTRY_PROJECT,
        'SENTRY_ENVIRONMENT': settings.SENTRY_ENVIRONMENT,
    }
    if request.method == 'POST':
        form = SentryForm(request.POST)
        if form.is_valid():
            last_event_id = None
            opt = form.cleaned_data['action']
            if opt == 'capture_event':
                last_event_id = sentry_sdk.capture_event({'capture_event() Test': 1})
            elif opt == 'capture_exception':
                last_event_id = sentry_sdk.capture_exception(Exception('capture_exception() Test'))
            elif opt == 'capture_message':
                last_event_id = sentry_sdk.capture_message('capture_message() Test')
            elif opt == 'logging_integration':
                try:
                    raise Exception('Logging Integration/last_event_id() Test')
                except Exception as e:
                    logger.exception(e)
                    last_event_id = sentry_sdk.last_event_id()
            elif opt in ['403', '404', '500']:
                from krm3.web.views.errors import error_403_view, error_404_view, error_500_view

                mapping = {
                    '403': (PermissionDenied, error_403_view),
                    '404': (Http404, error_404_view),
                    '500': (Exception, error_500_view),
                }
                error, handler = mapping[opt]
                try:
                    raise error(f'Error {opt} Test')
                except Exception as e:
                    logger.exception(e)
                    return handler(request, e)
            messages.add_message(request, messages.SUCCESS, f'Sentry ID: {last_event_id}')

    else:
        form = SentryForm()
    context['form'] = form
    return render(request, 'admin/console/sentry.html', context)
