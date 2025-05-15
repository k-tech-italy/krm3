"""KRM3 URL Configuration

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
from pathlib import Path

from adminactions import actions
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin import site
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
import krm3.fe


# from rest_framework.routers import DefaultRouter
#
# router = DefaultRouter()
admin.autodiscover()
actions.add_to_site(site)

# see https://djoser.readthedocs.io/en/latest/getting_started.html
urlpatterns = [
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),

    path('api/v1/', include('djoser.urls')),
    # # path('', include('djoser.urls.authtoken')),
    path('api/v1/', include('djoser.urls.jwt')),
    path('api/v1/', include('djoser.social.urls')),  # Needed for social authentication
    # path('api/v1/jwt/logout/', BlacklistRefreshView.as_view(), name='jwtlogout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    # http://localhost:8000/oauth/complete/google-oauth2/
    path('be/', include('krm3.web.urls')),

    path('api/v1/', include('krm3.api.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include('krm3.fe.urls')),

]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.insert(0, path('__debug__/', include(debug_toolbar.urls)), )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    ) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

if settings.RELOAD:
    urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))
