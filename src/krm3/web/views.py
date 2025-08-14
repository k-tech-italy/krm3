import logging
from typing import Any

from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from krm3.timesheet.availability_report import availability_report_data

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
            'Availability report': reverse('availability'),
        }

        return context

class AvailabilityReportView(HomeView):
    # TODO add permission check
    login_url = '/admin/login/'
    template_name = 'availability_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | availability_report_data(current_month)
