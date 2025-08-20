import logging
from typing import Any, cast
from django.http import HttpRequest, HttpResponseBase

from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from krm3.timesheet.availability_report import availability_report_data
from krm3.timesheet.report import timesheet_report_data
from krm3.timesheet.task_report import task_report_data

logger = logging.getLogger(__name__)

User = get_user_model()


class HomeView(LoginRequiredMixin, TemplateView):
    login_url = '/admin/login/'
    template_name = 'home.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['nav_bar_items'] = {
            'Report': reverse('report'),
            'Report by task': reverse('task_report'),
            'Availability report': reverse('availability'),
        }

        return context


class ReportPermissionView(HomeView):

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        user = cast('User', request.user)
        if not user.is_anonymous and not user.has_any_perm(
            'core.manage_any_timesheet', 'core.view_any_timesheet'
        ):
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


class AvailabilityReportView(HomeView):
    template_name = 'availability_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | availability_report_data(current_month)


class ReportView(ReportPermissionView):
    template_name = 'report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | timesheet_report_data(current_month)


class TaskReportView(ReportPermissionView):
    template_name = 'task_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | task_report_data(current_month)
