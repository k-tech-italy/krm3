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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

from krm3.core.views import BlacklistRefreshView

# see https://djoser.readthedocs.io/en/latest/getting_started.html
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('djoser.urls')),
    # path('', include('djoser.urls.authtoken')),
    path('api/v1/', include('djoser.urls.jwt')),
    path('api/v1/', include('djoser.social.urls')),  # Needed for social authentication
    path('api/v1/jwt/logout/', BlacklistRefreshView.as_view(), name='jwtlogout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    # http://localhost:8000/oauth/complete/google-oauth2/
    path('', include('krm3.web.urls')),

    path('api/v1/', include('krm3.api.urls')),
    path('swagger-ui/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui'),
    path('openapi', get_schema_view(
        title='Your Project',
        description='API for all things …',
        version='1.0.0'
    ), name='openapi-schema'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.insert(0, path('__debug__/', include(debug_toolbar.urls)), )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    ) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
