import decimal
import json
from decimal import Decimal

import sentry_sdk
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from adminfilters.num import NumberFilter
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin, site
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
from krm3.styles.buttons import NORMAL
from krm3.utils.filters import RecentFilter
from krm3.utils.queryset import ACLMixin
from krm3.utils.rates import update_rates

NON_RIMBORSATE = 'Non Rimborsate'

GIA_RIMBORSATE = 'Già Rimborsate'

TOTALE_RIMBORSO = 'Totale Rimborso'

ANTICIPATO = 'Anticipato'

SPESE_TRASFERTA = 'Spese trasferta'


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

    def get_changeform_initial_data(self, request):
        ret = super().get_changeform_initial_data(request)
        if not request.user.has_perm('missions.manage_any_mission'):
            ret['resource'] = request.user.resource
        return ret

    @admin.action(description='Export selected missions')
    def export(self, request, queryset):
        pathname = MissionExporter(queryset).export()
        response = FileResponse(open(pathname, 'rb'))
        return response

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('expenses')

    def expense_num(self, obj: Reimbursement):
        return obj.expense_count

    expense_num.short_description = 'Num expenses'

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'default_currency':
            kwargs['queryset'] = Currency.objects.actives()
        return super(MissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    @button(html_attrs=NORMAL, visible=lambda btn: btn.original.status == Mission.MissionStatus.DRAFT)
    def submit(self, request, pk: int):
        mission = Mission.objects.get(pk=pk)
        if mission.status == Mission.MissionStatus.DRAFT:
            mission.status = Mission.MissionStatus.SUBMITTED
            if mission.number is None:
                mission.number = Mission.calculate_number(mission.id, mission.year)
            mission.save()
        else:
            messages.warning(request, f'Cannot change status {mission.status} to {Mission.MissionStatus.SUBMITTED}')

    @button(html_attrs=NORMAL, visible=lambda btn: bool(Reimbursement.objects.filter(expenses__mission=btn.original)))
    def view_linked_reimbursements(self, request, pk: int):
        rids = map(str, Reimbursement.objects.filter(expenses__mission_id=pk).values_list('id', flat=True))
        return redirect(reverse('admin:core_reimbursement_changelist') + f'?id__in={",".join(rids)}')

    @button(
        html_attrs=NORMAL,
    )
    def add_expense(self, request, pk: int):
        mission = Mission.objects.get(pk=pk)
        from_date = mission.from_date.strftime('%Y-%m-%d')
        return redirect(reverse('admin:core_expense_add') + f'?mission_id={pk}&day={from_date}')

    @button(
        html_attrs=NORMAL,
        visible=lambda button: button.request.user.has_perm('missions.manage_any_mission'),
    )
    def import_missions(self, request):  # noqa: D102
        if request.method == 'POST':
            form = MissionsImportForm(request.POST, request.FILES)
            if form.is_valid():
                target = MissionImporter(request.FILES['file']).store()
                data = MissionImporter.get_data(target)

                data = json.dumps(data, indent=4)

                return TemplateResponse(
                    request, context={'data': data}, template='admin/missions/mission/import_missions_check.html'
                )
        else:
            form = MissionsImportForm()
            return TemplateResponse(
                request, context={'form': form}, template='admin/missions/mission/import_missions.html'
            )

    @button(
        html_attrs=NORMAL,
    )
    def overview(self, request, pk: int):
        mission = self.get_object(request, pk)
        sorting = request.GET.get('sort')
        qs = mission.expenses.all()

        try:
            if export_format := request.GET.get('_export', None):
                expenses = self.build_mission_expenses_table(qs, sorting, True)
                return self.export_table(mission, expenses, export_format, request)
            expenses = self.build_mission_expenses_table(qs, sorting)

            summary = {
                SPESE_TRASFERTA: decimal.Decimal(0.0),
                ANTICIPATO: decimal.Decimal(0.0),
                TOTALE_RIMBORSO: decimal.Decimal(0.0),
                GIA_RIMBORSATE: decimal.Decimal(0.0),
                # 'Ancora da rimborsare': decimal.Decimal(0.0),
                NON_RIMBORSATE: decimal.Decimal(0.0),
            }

            for expense in qs:
                expense: Expense
                summary[ANTICIPATO] += (
                    expense.amount_base if expense.payment_type.personal_expense is False else decimal.Decimal(0.0)
                )
                summary[TOTALE_RIMBORSO] += expense.amount_reimbursement or decimal.Decimal(0.0)
                summary[GIA_RIMBORSATE] += (
                    expense.amount_reimbursement
                    if expense.reimbursement
                    else decimal.Decimal(0.0) or decimal.Decimal(0.0)
                )
                summary[NON_RIMBORSATE] += (
                    (expense.amount_base or decimal.Decimal(0.0))
                    - (expense.amount_reimbursement or decimal.Decimal(0.0))
                    if expense.payment_type.personal_expense
                    else decimal.Decimal(0.0)
                )
                summary[SPESE_TRASFERTA] += (
                    expense.amount_base
                    if not expense.payment_type.personal_expense
                    else expense.amount_reimbursement or Decimal('0')
                ) or decimal.Decimal(0.0)

            da_rimborsare = summary[SPESE_TRASFERTA] - summary[ANTICIPATO] - summary[GIA_RIMBORSATE]
            summary[TOTALE_RIMBORSO] = (
                f'{summary[TOTALE_RIMBORSO]} ({summary.pop(GIA_RIMBORSATE)} già Rimborsate, {da_rimborsare} rimanenti)'
            )

            return TemplateResponse(
                request,
                context={
                    'site_header': site.site_header,
                    'mission': mission,
                    'expenses': expenses,
                    'summary': summary,
                    'base': settings.BASE_CURRENCY,
                    'filename': format_html(f'{slugify(str(mission))}.pdf'),
                },
                template='admin/missions/mission/summary.html',
            )
        except RuntimeError as e:
            sentry_sdk.capture_exception(e)
            messages.error(request, str(e))

    def build_mission_expenses_table(self, qs, sorting, report=False):
        klass = MissionExpenseExportTable if report else MissionExpenseTable
        update_rates(qs)
        return klass(qs, order_by=[sorting] if sorting else ['day'])

    def export_table(self, mission: Mission, table_data, export_format, request):
        """Export django table data."""
        from django_tables2.config import RequestConfig

        RequestConfig(request).configure(table_data)

        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table_data)
            return exporter.response(f'mission_{mission.year}_{mission.number}_expenses.{export_format}')
        return None

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def view_expenses(self, request, pk: int):
        url = reverse('admin:core_expense_changelist') + f'?mission_id={pk}'
        return HttpResponseRedirect(url)
