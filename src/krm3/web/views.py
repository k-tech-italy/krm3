import datetime
import logging
import typing
from pathlib import Path
from typing import Any

import markdown
import openpyxl
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import TemplateView

from krm3.core.models.projects import Project
from krm3.timesheet.availability_report import availability_report_data
from krm3.timesheet.report.payslip import TimesheetReportOnline
from krm3.timesheet.report.payslip_report import TimesheetReportExport
from krm3.timesheet.task_report import task_report_data
from krm3.web.report_styles import centered, header_alignment, header_fill, header_font, nwd_fill, thin_border

if typing.TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

    from krm3.core.models import Contract

logger = logging.getLogger(__name__)

User = get_user_model()


class ReportMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['nav_bar_items'] = {
            'Report': reverse('report'),
            'Report by task': reverse('task_report'),
            'Availability report': reverse('availability'),
            'Releases': reverse('releases'),
        }
        context['logout_url'] = reverse('logout')

        return context


class HomeView(LoginRequiredMixin, TemplateView):
    login_url = '/admin/login/'
    template_name = 'home.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['nav_bar_items'] = {
            'Report': reverse('report'),
            'Report by task': reverse('task_report'),
            'Availability report': reverse('availability'),
            'Releases': reverse('releases'),
        }
        context['logout_url'] = reverse('logout')

        return context


class AvailabilityReportView(HomeView):
    template_name = 'availability_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        selected_project = self.request.GET.get('project', '')
        projects = {'': 'All projects'} | dict(Project.objects.values_list('id', 'name'))
        data = availability_report_data(current_month, selected_project)
        data['projects'] = projects
        data['selected_project'] = selected_project
        return context | data


def _write_resource_data(ws: 'Worksheet', data: dict, report_data: dict, current_row: int) -> int:
    """Write all data rows for a resource."""
    if not data:
        return current_row

    for key, value in data.items():
        if key in report_data['keymap']:
            safe_value = ['' if v is None else v for v in value]
            row_data = [report_data['keymap'][key], *safe_value]

            for col, cell_value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col, value=cell_value)
                if col > 1:
                    cell.alignment = centered
            current_row += 1

    return current_row


def export_report(request: HttpRequest, report_data: dict, date: str) -> HttpResponse:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Report {date[0:4]}-{date[4:6]}'

    ws.column_dimensions['A'].width = 30

    current_row = 1

    for resource_idx, (resource, data) in enumerate(report_data['data'].items(), start=1):
        if data is None:
            continue

        # spacing between employees
        if resource_idx > 1:
            current_row += 2

        holidays = []
        overlapping_contracts: 'list[Contract]' = resource.get_contracts(min(data['days']).date, max(data['days']).date)

        for day in data['days']:
            contract = resource.contract_for_date(overlapping_contracts, day)
            calendar_code = contract.country_calendar_code if contract else None
            holidays.append('X' if day.is_holiday(calendar_code) else '')

        # Header section
        headers = [
            f'{resource_idx} - {resource.last_name.upper()} {resource.first_name}',
            'Tot HH',
            *holidays,
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = header_alignment

        current_row += 1

        # Days row
        giorni = [
            'Giorni',
            '',
            *[
                f'{"**" if not day.submitted else ""}{day.day_of_week_short}\n{day.day}'
                f'{"**" if not day.submitted else ""}'
                for day in data['days']
            ],
        ]
        for col, giorno in enumerate(giorni):
            cell = ws.cell(row=current_row, column=col + 1, value=giorno)
            cell.alignment = header_alignment
            if col > 1 and (data['days'][col - 2].is_holiday() or data['days'][col - 2].min_working_hours == 0):
                cell.fill = nwd_fill

        current_row += 1

        current_row = _write_resource_data(ws, data, report_data, current_row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f'report_{date[0:4]}-{date[4:6]}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


class ReportView(LoginRequiredMixin, ReportMixin, TemplateView):
    login_url = '/admin/login/'
    template_name = 'report.html'

    def get(self, request: HttpRequest, *args, month: str = None, export: bool = False, **kwargs) -> HttpResponse:
        self.month = month
        if export:
            ctx = self._get_base_context()
            title = ctx['title']
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            filename = f'report_{slugify(title)}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            report = TimesheetReportExport(ctx['start'], ctx['end'], self.request.user)

            report.write_excel(response, f'Report risorse {title}')
            return response
        return super().get(request, *args, **kwargs)

    def _get_base_context(self) -> dict:
        if self.month is None:
            start_of_month = datetime.date.today().replace(day=1)
        else:
            start_of_month = datetime.datetime.strptime(self.month, '%Y%m').date()

        prev_month = start_of_month - relativedelta(months=1)
        next_month = start_of_month + relativedelta(months=1)

        return {
            'start': start_of_month,
            'end': start_of_month + relativedelta(months=1, days=-1),
            'current_month': start_of_month.strftime('%Y%m'),
            'prev_month': prev_month.strftime('%Y%m'),
            'next_month': next_month.strftime('%Y%m'),
            'title': {
                'January': 'Gennaio',
                'February': 'Febbraio',
                'March': 'Marzo',
                'April': 'Aprile',
                'May': 'Maggio',
                'June': 'Giugno',
                'July': 'Luglio',
                'August': 'Agosto',
                'September': 'Settembre',
                'October': 'Ottobre',
                'November': 'Novembre',
                'December': 'Dicembre',
            }.get(start_of_month.strftime('%B'))
            + f'{start_of_month.strftime(" %Y")}',
        }

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self._get_base_context())

        report_blocks = TimesheetReportOnline(ctx['start'], ctx['end'], self.request.user)
        ctx['report_blocks'] = report_blocks.report_html()
        return ctx


class TaskReportView(HomeView):
    template_name = 'task_report.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        current_month = self.request.GET.get('month')
        return context | task_report_data(current_month, user=self.request.user)


class ReleasesView(HomeView):
    template_name = 'releases.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        project_root = Path(settings.BASE_DIR).parent.parent
        changelog_file_path = project_root / 'CHANGELOG.md'
        changelog_html = ''

        try:
            changelog_content = Path(changelog_file_path).read_text(encoding='utf-8')
            changelog_html = markdown.markdown(changelog_content)

            soup = BeautifulSoup(changelog_html, 'html.parser')
            for h2 in soup.find_all('h2'):
                h2['class'] = h2.get('class', []) + [
                    'text-2xl',
                    'text-blue-300',
                    'border-b',
                    'border-white/20',
                    'pb-2',
                    'mb-4',
                    'mt-6',
                    'font-semibold',
                ]

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
            logger.warning(f'CHANGELOG.md file not found at {changelog_file_path}')
            changelog_html = "<p class='text-gray-400'>CHANGELOG.md file not found.</p>"
        except (OSError, UnicodeDecodeError) as e:
            logger.error(f'Error parsing CHANGELOG.md: {e}')
            changelog_html = f"<p class='text-red-400'>Error parsing CHANGELOG.md: {e}</p>"

        context['changelog_html'] = changelog_html
        return context
