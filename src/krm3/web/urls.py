from django.urls import path
from django.views.generic import TemplateView

from .views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    # ...
    # Route TemplateView to serve Swagger UI template.
    #   * Provide `extra_context` with view name of `SchemaView`.
    path('swagger-ui/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui'),
]
