from cryptography.fernet import Fernet

from ..environ import env as _env

SECRET_KEY = _env('SECRET_KEY')

ALLOWED_HOSTS = _env('ALLOWED_HOSTS')
INTERNAL_IPS = _env('INTERNAL_IPS')

SECURE_HSTS_SECONDS = _env('SECURE_HSTS_SECONDS')
if _env('SECURE_PROXY_SSL_HEADER'):
    SECURE_PROXY_SSL_HEADER = _env('SECURE_PROXY_SSL_HEADER')
SECURE_HSTS_PRELOAD = _env('SECURE_HSTS_PRELOAD')
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = _env('CSRF_COOKIE_SAMESITE')
SESSION_COOKIE_SAMESITE = _env('SESSION_COOKIE_SAMESITE')
SECURE_SSL_REDIRECT = _env('SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT

CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = _env('CSRF_TRUSTED_ORIGINS')

_proto = 'https' if SECURE_SSL_REDIRECT else 'http'
CORS_ALLOWED_ORIGINS = [f'{_proto}://{x}:8000' for x in ALLOWED_HOSTS]
CORS_ALLOWED_ORIGINS.extend([f'{_proto}://{x}:3000' for x in ALLOWED_HOSTS])

CORS_ORIGIN_WHITELIST = [f'{_proto}://{x}:8000' for x in ALLOWED_HOSTS]
CORS_ORIGIN_WHITELIST.extend([f'{_proto}://{x}:3000' for x in ALLOWED_HOSTS])
FORCE_DEBUG_SSL = _env('FORCE_DEBUG_SSL')

CORS_ALLOW_CREDENTIALS = True

FERNET_KEY = Fernet(_env('FERNET_KEY'))

if _env('DEBUG'):
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

LOGOUT_REDIRECT_URL='/logout'
