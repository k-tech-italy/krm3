#  :copyright: Copyright (c) 2018-2020. OS4D Ltd - All Rights Reserved
#  :license: Commercial
#  Unauthorized copying of this file, via any medium is strictly prohibited
#  Written by Stefano Apostolico <s.apostolico@gmail.com>, October 2020

import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from django.utils.crypto import get_random_string
from krm3.utils.tools import parse_emails


DEFAULTS = dict(  # noqa: C408
    DATABASE_URL=(str, 'psql://postgres:@127.0.0.1:5432/krm3_db', 'The database URl'),
    DEBUG=(bool, False),
    LOCAL_DEVELOPMENT=(bool, False, 'Enable local development mode to serve static files via Django'),
    RELOAD=(bool, False),
    DEV_FOOTER_INFO=(str, uuid.uuid4()),
    CV2_SHOW_IMAGES=(bool, False),
    EMAIL_BACKEND=(str, 'django.core.mail.backends.smtp.EmailBackend'),
    EMAIL_HOST=(str, 'smtp.gmail.com'),
    EMAIL_HOST_USER=(str, 'noreply@k-tech.it'),
    EMAIL_HOST_PASSWORD=(str, ''),
    EMAIL_FROM_EMAIL=(str, 'noreply@k-tech.it'),
    EMAIL_PORT=(int, 587),
    EMAIL_SUBJECT_PREFIX=(str, '[krm3]'),
    EMAIL_USE_LOCALTIME=(bool, False),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_USE_SSL=(bool, True),
    EMAIL_TIMEOUT=(int, 30),
    SENTRY_DSN=(str, ''),
    SENTRY_SECURITY_TOKEN=(str, ''),
    SENTRY_SECURITY_TOKEN_HEADER=(str, 'X-Sentry-Token'),
    SENTRY_DEBUG=(bool, False),
    SENTRY_ENVIRONMENT=(str, 'local'),
    MEDIA_ROOT=(str, str(Path(__file__).parent.parent.parent.parent / '~media')),
    MEDIA_URL=(str, '/media/'),
    STATIC_ROOT=(str, str(Path(__file__).parent.parent.parent.parent / '~static')),
    ADMINS=(parse_emails, ''),
    TEST_USERS=(parse_emails, ''),
    # # Security
    SECRET_KEY=(str, '--'),
    FERNET_KEY=(str, Fernet.generate_key().decode('utf-8')),
    INTERNAL_IPS=(list, ['127.0.0.1', 'localhost']),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_COOKIE_SAMESITE=(str, 'strict'),
    SESSION_COOKIE_SAMESITE=(str, 'lax'),
    CSRF_TRUSTED_ORIGINS=(list, ''),
    FORCE_DEBUG_SSL=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_PRELOAD=(bool, False),
    SECURE_PROXY_SSL_HEADER=(list, []),  # Set to "HTTP_X_FORWARDED_PROTO,https" behind SSL terminator
    SECURE_SSL_REDIRECT=(bool, False),
    USE_X_FORWARDED_HOST=(bool, 'false'),
    USE_HTTPS=(bool, False),
    ADMIN_USERNAME=(str, 'admin'),
    ADMIN_FIRSTNAME=(str, 'admin'),
    ADMIN_LASTNAME=(str, 'admin'),
    ADMIN_PASSWORD=(str, 'admin'),
    ADMIN_EMAIL=(str, 'noreply@k-tech.it'),
    # django_money
    CURRENCY_CHOICES=(list, ['GBP', 'EUR', 'USD']),
    BASE_CURRENCY=(str, 'EUR'),
    OPEN_EXCHANGE_RATES_APP_ID=(str, ''),
    DECIMAL_DIGITS=(int, 2),
    CURRENCY_FORMAT=(str, '{:,.2f}'),
    # # Django debug toolbar
    DDT_KEY=(str, get_random_string(length=12)),
    DDT_PANELS=(
        list,
        [
            'debug_toolbar.panels.timer.TimerPanel',
            'debug_toolbar.panels.settings.SettingsPanel',
            'debug_toolbar.panels.headers.HeadersPanel',
            'debug_toolbar.panels.request.RequestPanel',
            'debug_toolbar.panels.sql.SQLPanel',
            'debug_toolbar.panels.staticfiles.StaticFilesPanel',
            'debug_toolbar.panels.templates.TemplatesPanel',
            # 'debug_toolbar.panels.logging.LoggingPanel',
            'debug_toolbar.panels.redirects.RedirectsPanel',
            'debug_toolbar.panels.signals.SignalsPanel',
            'debug_toolbar.panels.profiling.ProfilingPanel',
        ],
    ),
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=(str, '543837936941-6cvmpg79fc93jfq2fv3e4qvtuib3cq9n.apps.googleusercontent.com'),
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=(str, ''),
    SOCIAL_AUTH_ALLOWED_REDIRECT_URIS=(list, ['http://localhost:3000/login', 'http://localhost:8000/login']),
    SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS=(list, ['k-tech.it']),
    HOLIDAYS_CALENDAR=(str, 'IT-RM'),
    DEFAULT_MODULE=(str, None),
    # Ticketing
    TICKETING_TOKEN=(str, None),
    TICKETING_PROJECT_ID=(int, None),
    TICKETING_ISSUES=(str, None),
    TICKETING_URL=(str, None),
    URL_REPLACE=(dict, None),
)
