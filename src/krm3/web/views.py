import json
import logging
import os
import typing
from typing import Any, cast
import openpyxl
from django.http import HttpRequest, HttpResponseBase, HttpResponse

from django.urls import reverse
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from krm3.config import settings
from krm3.core.models.projects import Project
from krm3.timesheet.availability_report import availability_report_data
from krm3.timesheet.report import timesheet_report_data
from krm3.timesheet.task_report import task_report_data

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract

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
            'Releases': reverse('releases')
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
        selected_project = self.request.GET.get('project', '')
        projects = {
            '': 'All projects'
        } | dict(Project.objects.values_list('id', 'name'))
        data = availability_report_data(current_month, selected_project)
        data['projects'] = projects
        data['selected_project'] = selected_project
        return context | data


def export_report(date: str) -> Response:
    report_data = timesheet_report_data(date)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for resource, data in report_data['data'].items():
        if data is None:
            continue
        holidays = []
        overlapping_contracts: 'list[Contract]' = resource.get_contracts(min(data['days']).date, max(data['days']).date)
        for day in data['days']:
            contract = resource.contract_for_date(overlapping_contracts, day)
            calendar_code = contract.country_calendar_code if contract else None
            holidays.append('X' if day.is_holiday(calendar_code) else '')

        headers = [
            name := f'{resource.last_name.upper()} {resource.first_name}',
            'Tot HH',
            *holidays,
        ]

        ws = wb.create_sheet(title=name)
        ws.append(headers)

        giorni = [
            'Giorni',
            '',
            *[
                f'{"**" if not day.submitted else ""}{day.day_of_week_short}\n{day.day}'
                f'{"**" if not day.submitted else ""}'
                for day in data['days']
            ],
        ]
        ws.append(giorni)

        if data:
            for key, value in data.items():
                if key in report_data['keymap']:
                    safe_value = ['' if v is None else v for v in value]
                    row = [report_data['keymap'][key], *safe_value]
                    ws.append(row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f'report_{date[0:4]}-{date[4:6]}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


class ReportView(ReportPermissionView):
    template_name = 'report.html'

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if kwargs.get('export'):
            date = kwargs.get('date')
            return export_report(date)
        return super().get(request, *args, **kwargs)

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


class ReleasesView(HomeView):
    template_name = 'releases.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        releases_file_path = os.path.join(settings.BASE_DIR, 'releases.json')
        releases_data = {}

        try:
            with open(releases_file_path, encoding='utf-8') as file:
                releases_data = json.load(file)
        except FileNotFoundError:
            logger.warning(f"Releases file not found at {releases_file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing releases.json: {e}")

        context['releases'] = releases_data
        return context
