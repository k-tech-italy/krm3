"""KRM3 URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from adminactions import actions
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin import site
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from debug_toolbar.toolbar import debug_toolbar_urls

from krm3.config.environ import env

admin.autodiscover()
actions.add_to_site(site)


def trigger_error(*args) -> None:
    division_by_zero = 1 / 0  # noqa: F841


# see https://djoser.readthedocs.io/en/latest/getting_started.html
urlpatterns = [
    path('', include('pwa.urls')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('api/v1/', include('djoser.urls')),
    path('api/v1/', include('djoser.urls.jwt')),
    path('api/v1/', include('djoser.social.urls')),  # Needed for social authentication
    path('oauth/', include('social_django.urls', namespace='social')),
    # http://localhost:8000/oauth/complete/google-oauth2/
    path('be/', include('krm3.web.urls')),
    path('api/v1/', include('krm3.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('sentry-debug/', trigger_error),
    path('', include('krm3.fe.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if token := env('TICKETING_TOKEN'):
    urlpatterns.insert(0, path('be/ticketing/', include('issues.urls', namespace='issues')))

if settings.DEBUG:
    urlpatterns = (
        urlpatterns
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )

if not settings.TESTING:
    urlpatterns = debug_toolbar_urls() + urlpatterns

if settings.RELOAD:
    urlpatterns.append(path('__reload__/', include('django_browser_reload.urls')))
