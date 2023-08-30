"""
Django settings for krm3 project.

Generated by 'django-admin startproject' using Django 3.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import logging
import os
from pathlib import Path

from django_regex.utils import RegexList

import krm3
from krm3.config.fragments.constance import *  # noqa: F401,F403
from krm3.config.fragments.security import *  # noqa: F401,F403
from krm3.config.fragments.sentry import *  # noqa: F401,F403
from krm3.config.fragments.social import *  # noqa: F401,F403

from .environ import env
from .fragments.smartadmin import *  # noqa: F401,F403

logger = logging.getLogger(__name__)

AUTH_USER_MODEL = 'core.User'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_ROOT = env('MEDIA_ROOT')
MEDIA_URL = env('MEDIA_URL')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

INSTALLED_APPS = [
    # 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admindocs',
    'django.contrib.sites',

    'django_sysinfo',
    'adminactions',
    'adminfilters',
    'admin_extra_buttons',
] + SMART_ADMIN_APPS + [  # noqa: F405 we import it from smartadmin fragment

    # Project apps.
    'krm3.config.admin_extras.apps.AdminConfig',
    'krm3.core',
    'krm3',
    'krm3.currencies',
    'krm3.missions',
    'krm3.api',

    # Third party apps.
    'qr_code',
    'django_filters',
    'rest_framework',
    'drf_spectacular',
    'djoser',
    # 'corsheaders',
    'mptt',
    'social_django',
    'crispy_forms',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_tables2',
    'constance'
]

SITE_ID = 1

try:
    import django_extensions as _  # noqa: F401
    INSTALLED_APPS.append('django_extensions')
except ModuleNotFoundError:
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'corsheaders.middleware.CorsMiddleware',
    ] + SOCIAL_MIDDLEWARES + [  # noqa: F405
    'django.contrib.admindocs.middleware.XViewMiddleware',
    # Third party middlewares.
]

ROOT_URLCONF = 'krm3.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'web/templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ] + SOCIAL_TEMPLATE_PROCESSORS + [  # noqa: F405
                'django.template.context_processors.request'
            ],
        },
    },
]

WSGI_APPLICATION = 'krm3.config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': env.db('DATABASE_URL'),
}

DATABASES['default']['OPTIONS'] = {'options': '-c search_path=django,public'}
# DATABASES['default']['ENGINE'] = 'krm3.utils.db.postgresql'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []
else:
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_ROOT = env('STATIC_ROOT')
STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ADMINS = env('ADMINS')
TEST_USERS = env('TEST_USERS')

SYSINFO = {
    'extra': {
        'GIT': 'krm3.utils.sysinfo.get_commit_info',
    },
    'masker': 'krm3.utils.sysinfo.masker',
}

# Debug toolbar
if ddt_key := env('DDT_KEY'):
    try:
        ignored = RegexList(('/api/.*',))

        def show_ddt(request):
            """Runtime check for showing debug toolbar."""
            if not DEBUG:
                return False
            # use https://bewisse.com/modheader/ to set custom header
            # key must be `DDT-KEY` (no HTTP_ prefix, no underscores)
            if request.user.is_authenticated:
                if request.path in ignored:
                    return False
            return request.META.get('HTTP_DDT_KEY') == ddt_key

        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': show_ddt,
            'JQUERY_URL': '',
        }
        DEBUG_TOOLBAR_PANELS = env('DDT_PANELS')

        # Testing for debug_toolbar presence
        import debug_toolbar  # noqa: F401

        MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
        INSTALLED_APPS.append('debug_toolbar')
        # CSP_REPORT_ONLY = True
    except ImportError:
        logger.info('Skipping debug toolbar')


CURRENCY_BASE = env('CURRENCY_BASE')
CURRENCIES = env('CURRENCY_CHOICES')

if oerai := env('OPEN_EXCHANGE_RATES_APP_ID'):
    OPEN_EXCHANGE_RATES_APP_ID = oerai


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'KRM3 API',
    'DESCRIPTION': 'A K-Tech internal project',
    'VERSION': krm3.__version__,
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1',
    # OTHER SETTINGS
}

AUTHENTICATION_BACKENDS += [  # noqa: F405
    'django.contrib.auth.backends.ModelBackend',
]
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'


# Shows CV2 intermediate processing images. For Local dev only
CV2_SHOW_IMAGES = env('CV2_SHOW_IMAGES')
