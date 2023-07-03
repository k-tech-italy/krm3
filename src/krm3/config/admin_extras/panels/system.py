"""System admin panel module."""
import logging

from django.contrib import messages
from django.shortcuts import render

logger = logging.getLogger(__name__)


def get_info():  # noqa: D103
    try:
        return {
        }
    except Exception as e:
        return {'error': str(e)}


def system_panel(self, request, extra_context=None):  # noqa: D103
    context = self.each_context(request)
    try:
        from django.core.mail import get_connection

        conn = get_connection()
        context['results'] = {
            'Info': get_info(),
        }
        context['connection'] = conn

    except Exception as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR, f'{e.__class__.__name__}: {e}')

    return render(request, 'admin/console/system.html', context)


system_panel.verbose_name = 'System Checks'
