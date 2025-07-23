import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

class HomeView(LoginRequiredMixin, TemplateView):
    login_url = '/admin/login/'
    template_name = 'home.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['nav_bar_items'] = {
            'Report': reverse('admin:core_timeentry_report'),
            'Report by task': reverse('admin:core_timeentry_task_report'),
        }

        return context


def social_login(request: HttpRequest) -> HttpResponse:
    return render(request, 'social_login.html')


class ExampleView(TemplateView):
    """Home view."""

    template_name = 'example.html'
