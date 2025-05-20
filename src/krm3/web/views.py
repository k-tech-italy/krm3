import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView

logger = logging.getLogger(__name__)


class HomeView(RedirectView):
    def get_redirect_url(self, *args, **kwargs) -> str:
        return reverse('admin:index')


def social_login(request: HttpRequest) -> HttpResponse:
    return render(request, 'social_login.html')


class ExampleView(TemplateView):
    """Home view."""

    template_name = 'example.html'
