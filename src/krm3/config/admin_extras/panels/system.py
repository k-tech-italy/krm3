"""System admin panel module."""

import logging
from typing import TYPE_CHECKING, Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

if TYPE_CHECKING:
    from smart_admin.site import SmartAdminSite

logger = logging.getLogger(__name__)


def get_info() -> dict[str, str]:  # noqa: D103
    try:
        return {}
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)}


def system_panel(
    self: 'SmartAdminSite', request: HttpRequest, extra_context: dict[str, Any] | None = None
) -> HttpResponse:  # noqa: D103
    context = self.each_context(request)
    try:
        from django.core.mail import get_connection  # noqa: PLC0415

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
