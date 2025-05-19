import logging

from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import RedirectView

logger = logging.getLogger(__name__)


class HomeView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('admin:index')


def social_login(request: HttpRequest):
    return render(request, 'social_login.html')
