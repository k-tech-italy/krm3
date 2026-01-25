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

from __future__ import annotations

import typing

from adminactions import actions
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin import site
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from krm3.config.environ import env

admin.autodiscover()
actions.add_to_site(site)

if typing.TYPE_CHECKING:
    from django.http import FileResponse, HttpRequest



@login_required
def protected_serve(
    request: HttpRequest, path: str, document_root: str | None = None, show_indexes: bool = False
) -> FileResponse:
    return serve(request, path, document_root, show_indexes)


urlpatterns = [
    path('', include('pwa.urls')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('oauth/', include('social_django.urls', namespace='social')),
    # http://localhost:8000/oauth/complete/google-oauth2/
    path('be/', include('krm3.web.urls')),
    path('api/v1/', include('krm3.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('media-auth/', include('krm3.core.media_urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if token := env('TICKETING_TOKEN'):
    urlpatterns.insert(0, path('be/ticketing/', include('issues.urls', namespace='issues')))

# Serve static files from reverse proxy in production
if settings.DEBUG:
    # Add static and media URLs before the catch-all fe pattern
    urlpatterns = (
        urlpatterns
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )

# Add fe catch-all pattern last so it doesn't interfere with other routes
# Only include in local development mode
# in production nginx serves static and media files
if settings.LOCAL_DEVELOPMENT:
    urlpatterns.append(
        re_path(rf'^{settings.MEDIA_URL[1:]}(?P<path>.*)$', protected_serve, {'document_root': settings.MEDIA_ROOT})
    )
    urlpatterns.append(path('', include('krm3.fe.urls')))

if not settings.TESTING:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = debug_toolbar_urls() + urlpatterns

if settings.RELOAD:
    urlpatterns.append(path('__reload__/', include('django_browser_reload.urls')))
