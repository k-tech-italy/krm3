#  :copyright: Copyright (c) 2018-2020. OS4D Ltd - All Rights Reserved
#  :license: Commercial
#  Unauthorized copying of this file, via any medium is strictly prohibited
#  Written by Stefano Apostolico <s.apostolico@gmail.com>, October 2020
import os
import tempfile
import uuid
from environ import Env
from pathlib import Path

from django.utils.crypto import get_random_string

def parse_emails(value):
    admins = value.split(',')
    v = [(a.split('@')[0].strip(), a.strip()) for a in admins]
    return v


DEFAULTS = {
    'ADMINS': (parse_emails, ''),
    'TEST_USERS': (parse_emails, ''),
    'ALLOWED_HOSTS': (list, ''),
    'DATABASE_URL': (str, 'psql://postgres:@127.0.0.1:5432/krm3_db'),
    'DEBUG': (bool, False),
    'DEV_FOOTER_INFO': (str, uuid.uuid4()),

    'EMAIL_BACKEND': (str, 'django.core.mail.backends.smtp.EmailBackend'),
    'EMAIL_HOST': (str, 'smtp.gmail.com'),
    'EMAIL_HOST_USER': (str, 'noreply@k-tech.it'),
    'EMAIL_HOST_PASSWORD': (str, ''),
    'EMAIL_FROM_EMAIL': (str, ''),
    'EMAIL_PORT': (int, 587),
    'EMAIL_SUBJECT_PREFIX': (str, '[krm3]'),
    'EMAIL_USE_LOCALTIME': (bool, False),
    'EMAIL_USE_TLS': (bool, True),
    'EMAIL_USE_SSL': (bool, False),
    'EMAIL_TIMEOUT': (int, 30),

    'INTERNAL_IPS': (list, ['127.0.0.1', 'localhost']),
    'SENTRY_DSN': (str, ''),
    'SENTRY_SECURITY_TOKEN': (str, ''),
    'SENTRY_SECURITY_TOKEN_HEADER': (str, 'X-Sentry-Token'),

    'MEDIA_ROOT': (str, os.path.join(tempfile.gettempdir(), 'krm3', 'media')),
    'STATIC_ROOT': (str, str(Path(__file__).parent.parent / 'web/static')),

    'USE_X_FORWARDED_HOST': (bool, 'false'),
    'USE_HTTPS': (bool, False),

    'ADMIN_USERNAME': (str, ''),
    'ADMIN_PASSWORD': (str, ''),
    'ADMIN_EMAIL': (str, ''),
}

env = Env(**DEFAULTS)
