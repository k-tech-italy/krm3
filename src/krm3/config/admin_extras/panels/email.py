"""Email panel module."""

import logging
from functools import partial

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render

from krm3.utils.reflect import fqn
from krm3.utils.sysinfo import masker
from krm3.utils.threading import runs_in_background

logger = logging.getLogger(__name__)


def email(self, request, extra_context=None):  # noqa: D103
    context = self.each_context(request)
    context['title'] = 'Email'
    context['smtp'] = {
        'EMAIL_BACKEND': settings.EMAIL_BACKEND,
        'EMAIL_HOST': settings.EMAIL_HOST,
        'EMAIL_PORT': settings.EMAIL_PORT,
        'EMAIL_HOST_PASSWORD': masker('EMAIL_HOST_PASSWORD', settings.EMAIL_HOST_PASSWORD, None, request),
        'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
        'EMAIL_USE_SSL': settings.EMAIL_USE_SSL,
        'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'EMAIL_SUBJECT_PREFIX': settings.EMAIL_SUBJECT_PREFIX,
    }
    if request.method == 'POST':

        def _run(func, **kwargs):
            try:
                func(**kwargs)
                context['results'][fqn(func)] = kwargs.get('to', kwargs.get('recipient_list'))
            except Exception as e:
                context['results'][fqn(func)] = f'{e.__class__.__name__}: {e}'

        try:
            from django.core.mail import get_connection

            conn = get_connection()
            context['results'] = {}
            context['connection'] = conn
            from django.core.mail import send_mail as django_send_mail

            from krm3.utils.threading import wait_for_tasks

            subject = lambda f: "%sSend email test: '%s" % (settings.EMAIL_SUBJECT_PREFIX, f)  # noqa: E731
            tasks = runs_in_background(
                [
                    (
                        partial(_run, django_send_mail),
                        [],
                        {
                            'subject': subject('django.core.mail.send_mail'),
                            'from_email': None,
                            'message': "Test send email using raw 'django.core.mail.send_mail'",
                            'recipient_list': [request.user.email],
                        },
                    ),
                ]
            )
            wait_for_tasks(tasks)
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, f'{e.__class__.__name__}: {e}')

    return render(request, 'admin/console/email.html', context)
