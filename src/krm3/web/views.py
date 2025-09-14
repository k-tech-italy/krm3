import logging
import typing
from pathlib import Path
from typing import Any, cast

import markdown
import openpyxl
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import HttpRequest, HttpResponseBase, HttpResponse

from django.urls import reverse
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

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
        context['logout_url'] = reverse('logout')

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
        project_root = Path(settings.BASE_DIR).parent.parent
        changelog_file_path = project_root / 'CHANGELOG.md'
        changelog_html = ""

        try:
            changelog_content = Path(changelog_file_path).read_text(encoding='utf-8')
            changelog_html = markdown.markdown(changelog_content)

            soup = BeautifulSoup(changelog_html, 'html.parser')
            for h2 in soup.find_all('h2'):
                h2['class'] = h2.get('class', []) + ['text-2xl', 'text-blue-300', 'border-b',
                                                     'border-white/20', 'pb-2', 'mb-4', 'mt-6', 'font-semibold']

            for h3 in soup.find_all('h3'):
                h3['class'] = h3.get('class', []) + ['text-xl', 'text-purple-300', 'mb-3', 'font-medium']

            for ul in soup.find_all('ul'):
                ul['class'] = ul.get('class', []) + ['space-y-2', 'my-4']

            for li in soup.find_all('li'):
                li['class'] = li.get('class', []) + ['marker:text-blue-400', 'marker:font-bold', 'ml-4']

            for p in soup.find_all('p'):
                p['class'] = p.get('class', []) + ['text-gray-200', 'leading-relaxed']

            for strong in soup.find_all('strong'):
                strong['class'] = strong.get('class', []) + ['text-white', 'font-semibold']

            changelog_html = str(soup)
        except FileNotFoundError:
            logger.warning(f"CHANGELOG.md file not found at {changelog_file_path}")
            changelog_html = "<p class='text-gray-400'>CHANGELOG.md file not found.</p>"
        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Error parsing CHANGELOG.md: {e}")
            changelog_html = f"<p class='text-red-400'>Error parsing CHANGELOG.md: {e}</p>"

        context['changelog_html'] = changelog_html
        return context
