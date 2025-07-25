import decimal
import json
import typing
from decimal import Decimal

import sentry_sdk
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from adminfilters.num import NumberFilter
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Count
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django_tables2.export import TableExport

from krm3.currencies.models import Currency
from krm3.missions.admin.expenses import ExpenseInline
from krm3.missions.forms import MissionAdminForm, MissionsImportForm
from krm3.missions.impexp.export import MissionExporter
from krm3.missions.impexp.imp import MissionImporter
from krm3.core.models import Expense, Mission, Reimbursement
from krm3.missions.tables import MissionExpenseExportTable, MissionExpenseTable
from krm3.missions.utilities import ReimbursementSummaryEnum
from krm3.styles.buttons import NORMAL
from krm3.utils.filters import RecentFilter
from krm3.utils.queryset import ACLMixin
from krm3.utils.rates import update_rates

if typing.TYPE_CHECKING:
    from krm3.missions.tables import MissionExpenseBaseTable
    from django.http import HttpRequest, HttpResponse
    from django.db.models import QuerySet


@admin.register(Mission)
class MissionAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin, ModelAdmin):
    save_on_top = True
    form = MissionAdminForm
    autocomplete_fields = ['project', 'city', 'resource']
    actions = ['export', 'reimburse']
    search_fields = ['resource__first_name', 'resource__last_name', 'title', 'project__name', 'city__name']

    inlines = [ExpenseInline]
    list_display = (
        'number',
        'year',
        'status',
        'resource',
        'project',
        'title',
        'from_date',
        'to_date',
        'default_currency',
        'city',
        'expense_num',
        'to_reimburse'
    )
    list_filter = [
        'status',
        RecentFilter,
        ('project', AutoCompleteFilter),
        ('city', AutoCompleteFilter),
        ('from_date', DateRangeFilter.factory(title='from YYYY-MM-DD')),
        ('to_date', DateRangeFilter.factory(title='to YYYY-MM-DD')),
        ('number', NumberFilter),
        'year',
    ]

    fieldsets = [
        (
            None,
            {
                'fields': [
                    ('number', 'year', 'status', 'title'),
                    ('from_date', 'to_date', 'default_currency'),
                    ('project', 'city', 'resource'),
                ]
            },
        )
    ]

    def get_changeform_initial_data(self, request: 'HttpRequest') -> dict:
        ret = super().get_changeform_initial_data(request)
        if not request.user.has_perm('missions.manage_any_mission'):
            ret['resource'] = request.user.resource
        return ret

    @admin.action(description='Export selected missions')
    def export(self, request: 'HttpRequest', queryset: 'QuerySet[Mission]') -> FileResponse:
        pathname = MissionExporter(queryset).export()
        with open(pathname, 'rb') as f:
            return FileResponse(f)

    def get_queryset(self, request: 'HttpRequest') -> 'QuerySet[Mission]':
        return (super().get_queryset(request).prefetch_related('expenses').annotate(expenses_count=Count('expenses'))
                .annotate(to_reimburse_count=Count('expenses', filter=Q(expenses__reimbursement_id__isnull=True))))

    @admin.display(description="Num expenses", ordering='expenses_count')
    def expense_num(self, obj: Reimbursement) -> int:
        return obj.expense_count

    @admin.display(description="To Reimburse", ordering='to_reimburse_count')
    def to_reimburse(self, obj: Reimbursement) -> int:
        return obj.expenses.filter(reimbursement_id__isnull=True).count()

    def formfield_for_foreignkey(
        self, db_field: models.ForeignKey, request: 'HttpRequest' = None, **kwargs
    ) -> forms.Field:
        if db_field.name == 'default_currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @button(html_attrs=NORMAL, visible=lambda btn: btn.original.status == Mission.MissionStatus.DRAFT)
    def submit(self, request: 'HttpRequest', pk: int) -> None:
        mission = Mission.objects.get(pk=pk)
        if mission.status == Mission.MissionStatus.DRAFT:
            mission.status = Mission.MissionStatus.SUBMITTED
            if mission.number is None:
                mission.number = Mission.calculate_number(mission.id, mission.year)
            mission.save()
        else:
            messages.warning(request, f'Cannot change status {mission.status} to {Mission.MissionStatus.SUBMITTED}')

    @button(html_attrs=NORMAL, visible=lambda btn: bool(Reimbursement.objects.filter(expenses__mission=btn.original)))
    def view_linked_reimbursements(self, request: 'HttpRequest', pk: int) -> 'HttpResponse':
        rids = map(str, Reimbursement.objects.filter(expenses__mission_id=pk).values_list('id', flat=True))
        return redirect(reverse('admin:core_reimbursement_changelist') + f'?id__in={",".join(rids)}')

    @button(
        html_attrs=NORMAL,
    )
    def add_expense(self, request: 'HttpRequest', pk: int) -> 'HttpResponse':
        mission = Mission.objects.get(pk=pk)
        from_date = mission.from_date.strftime('%Y-%m-%d')
        return redirect(reverse('admin:core_expense_add') + f'?mission_id={pk}&day={from_date}')

    @button(
        html_attrs=NORMAL,
        visible=lambda button: button.request.user.has_perm('missions.manage_any_mission'),
    )
    def import_missions(self, request: 'HttpRequest') -> 'HttpResponse':  # noqa: D102
        if request.method == 'POST':
            form = MissionsImportForm(request.POST, request.FILES)
            if form.is_valid():
                target = MissionImporter(request.FILES['file']).store()
                data = MissionImporter.get_data(target)
                data = json.dumps(data, indent=4)

                return TemplateResponse(
                    request, context={'data': data}, template='admin/missions/mission/import_missions_check.html'
                )
            return None
        form = MissionsImportForm()
        return TemplateResponse(request, context={'form': form}, template='admin/missions/mission/import_missions.html')

    @button(
        html_attrs=NORMAL,
    )
    def overview(self, request: 'HttpRequest', pk: int) -> 'HttpResponse':
        mission = self.get_object(request, pk)
        sorting = request.GET.get('sort')
        qs = mission.expenses.all()
        export_format = request.GET.get('_export', None)
        result_dict = {}

        try:
            if export_format:
                expenses_table = build_mission_expenses_table(qs, sorting, True)
                return self.export_table(mission, expenses_table, export_format, request)

            reimbursements = qs.values_list('reimbursement', flat=True).order_by('id').distinct()
            for reimbursement in reimbursements:
                exp_re = qs.filter(reimbursement_id=reimbursement)

                expenses_table = build_mission_expenses_table(exp_re, sorting)

                summary = {
                    ReimbursementSummaryEnum.SPESE_TRASFERTA: decimal.Decimal(0.0),
                    ReimbursementSummaryEnum.ANTICIPATO: decimal.Decimal(0.0),
                    ReimbursementSummaryEnum.TOTALE_RIMBORSO: decimal.Decimal(0.0),
                    ReimbursementSummaryEnum.GIA_RIMBORSATE: decimal.Decimal(0.0),
                    # 'Ancora da rimborsare': decimal.Decimal(0.0),
                    ReimbursementSummaryEnum.NON_RIMBORSATE: decimal.Decimal(0.0),
                    ReimbursementSummaryEnum.DA_RESTITUIRE: decimal.Decimal(0.0),
                }

                for expense in exp_re:
                    expense: Expense
                    summary[ReimbursementSummaryEnum.ANTICIPATO] += (
                        expense.amount_base if expense.payment_type.personal_expense is False else decimal.Decimal(0.0)
                    )
                    summary[ReimbursementSummaryEnum.TOTALE_RIMBORSO] += (
                        expense.amount_reimbursement or decimal.Decimal(0.0)
                    )

                    summary[ReimbursementSummaryEnum.GIA_RIMBORSATE] += (
                        expense.amount_reimbursement
                        if expense.reimbursement
                        else decimal.Decimal(0.0) or decimal.Decimal(0.0)
                    )
                    if expense.payment_type.personal_expense:
                        summary[ReimbursementSummaryEnum.NON_RIMBORSATE] += (
                            expense.amount_base or decimal.Decimal(0.0)
                        ) - (expense.amount_reimbursement or decimal.Decimal(0.0))
                    else:
                        summary[ReimbursementSummaryEnum.DA_RESTITUIRE] -= (
                            expense.amount_reimbursement or decimal.Decimal(0.0)
                        )

                    summary[ReimbursementSummaryEnum.SPESE_TRASFERTA] += (
                        expense.amount_base
                        if not expense.payment_type.personal_expense
                        else expense.amount_reimbursement or Decimal('0')
                    ) or decimal.Decimal(0.0)

                da_rimborsare = (
                    summary[ReimbursementSummaryEnum.TOTALE_RIMBORSO] - summary[ReimbursementSummaryEnum.GIA_RIMBORSATE]
                )
                summary[ReimbursementSummaryEnum.TOTALE_RIMBORSO] = (
                    f'{summary[ReimbursementSummaryEnum.TOTALE_RIMBORSO]}'
                    f' ({summary.pop(ReimbursementSummaryEnum.GIA_RIMBORSATE)}'
                    f' già Rimborsate, {da_rimborsare} rimanenti)'
                )
                result_dict[Reimbursement.objects.get(id=reimbursement) if reimbursement else None] = {
                    'expenses': expenses_table,
                    'summary': summary,
                }

            ctx = {
                'mission': mission,
                'reimbursement_breakdown': result_dict,
                'base': settings.BASE_CURRENCY,
                'filename': format_html(f'{slugify(str(mission))}.pdf'),
            }

            return TemplateResponse(
                request,
                context=ctx,
                template='admin/missions/mission/summary.html',
            )
        except RuntimeError as e:
            sentry_sdk.capture_exception(e)
            messages.error(request, str(e))

    def export_table(
        self, mission: Mission, table_data: dict, export_format: str, request: 'HttpRequest'
    ) -> 'HttpResponse | None':
        """Export django table data."""
        from django_tables2.config import RequestConfig

        RequestConfig(request).configure(table_data)

        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table_data)
            return exporter.response(f'mission_{mission.year}_{mission.number}_expenses.{export_format}')
        return None

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def view_expenses(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        url = reverse('admin:core_expense_changelist') + f'?mission_id={pk}'
        return HttpResponseRedirect(url)


def build_mission_expenses_table(qs: 'QuerySet', sorting: str, report: bool = False) -> 'MissionExpenseBaseTable':
    klass = MissionExpenseExportTable if report else MissionExpenseTable
    update_rates(qs)
    return klass(qs, order_by=[sorting] if sorting else ['day'])
