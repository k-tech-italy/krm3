import logging
from typing import Any
from django.http import HttpRequest, HttpResponseBase

from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from krm3.timesheet.availability_report import availability_report_data
from django.contrib.auth.views import redirect_to_login

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

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(), self.login_url, 'next'
            )
        if not request.user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):  # type: ignore
            raise PermissionDenied("You don't have permission to view this report.")
        return super().dispatch(request, *args, **kwargs)


class AvailabilityReportView(HomeView):
    template_name = 'availability_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | availability_report_data(current_month)
