from decimal import Decimal

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import site
from django.db.models import QuerySet, When, Case, Value, BooleanField, F
from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django_tables2.export import TableExport

from krm3.missions.admin.expenses import ExpenseInline
from krm3.missions.forms import ReimbursementAdminForm
from krm3.core.models import Mission, Reimbursement, Expense, Resource, ExpenseCategory
from krm3.missions.tables import ReimbursementExpenseExportTable, ReimbursementExpenseTable
from krm3.missions.utilities import calculate_reimbursement_summaries, ReimbursementSummaryEnum
from krm3.styles.buttons import NORMAL
from krm3.utils.filters import RecentFilter
from krm3.utils.queryset import ACLMixin
from krm3.utils.tools import uniq

summary_fields = ['tot_expenses', 'tot_company', 'forfait', 'to_reimburse', 'to_return', 'tot']


def prepare_resources_html(resources: dict, max_missions: int) -> dict:
    """Prepare data for reimbursement report template."""
    expense_categories = {str(x): x for x in ExpenseCategory.objects.all()}

    results = {}
    for resource_obj, mission_summaries in resources.items():
        missions = results.setdefault(str(resource_obj), [])
        tot = dict(zip(summary_fields, [Decimal('0.0')] * len(summary_fields), strict=False)) | {'n_mission': 'Tot'}
        for i, (mission_num, summary) in enumerate(mission_summaries.items()):
            missions.append(
                {
                    'n_mission': mission_num,
                    'tot_expenses': summary['summary'][ReimbursementSummaryEnum.TOTALE_COSTO],
                    'tot_company': summary['bypayment']['Company'][0],
                    'forfait': summary['byexpcategory'][expense_categories['Forfait']][0],
                    'to_reimburse': summary['bypayment']['Personal'][1],
                    'to_return': summary['bypayment']['Company'][1],
                }
            )
            missions[-1].update(
                {
                    'tot': missions[-1]['to_reimburse'] - missions[-1]['to_return'],
                }
            )

            for key in summary_fields:
                tot[key] += missions[i][key]
        missions.append(tot)

    return results


def prepare_reimbursement_report_context(queryset: QuerySet[Reimbursement]) -> dict:
    """Prepare data for reimbursement report template."""
    results = {}
    years_and_months = list(uniq(queryset.values_list('year', 'month').order_by('year', 'id', 'month')))
    for year, month in years_and_months:
        data = prepare_reimbursement_report_data(queryset.filter(year=year, month=month))
        results.setdefault(key := f'{month} {year}', {'resources': data})
        max_missions = max([len(v) for v in data.values()])
        results[key] = prepare_resources_html(results[key]['resources'], max_missions)
    return results


def prepare_reimbursement_report_data(queryset: QuerySet[Reimbursement]) -> dict:
    """Prepare data for reimbursement report for a specific month and year."""
    reimbursements_id = queryset.values_list('id', flat=True)
    # all expenses for reimbursements in queryset
    expenses_to_reimburse = Expense.objects.filter(reimbursement__in=queryset.values_list('id', flat=True))

    resource_and_mission = (
        expenses_to_reimburse.order_by(
            'reimbursement__resource__last_name', 'reimbursement__resource__first_name', 'mission__number'
        )
        .values_list('reimbursement__resource', 'mission')
        .distinct()
    )

    results = {}
    for resource_id, mission_id in resource_and_mission:
        resource_data = results.setdefault(Resource.objects.get(id=resource_id), {})
        mission = Mission.objects.get(pk=mission_id)
        expenses_in_mr = (
            Expense.objects.filter(
                reimbursement__in=queryset,
                mission=mission_id,
            )
            .annotate(personal_expense=F('payment_type__personal_expense'))
            .annotate(
                early=Case(
                    When(day__lt=mission.from_date, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
            .annotate(
                late=Case(
                    When(day__gt=mission.to_date, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
        )

        suffix = '*' if any(expenses_in_mr.values_list('early', flat=True)) else ''
        prefix = '^' if any(expenses_in_mr.values_list('late', flat=True)) else ''
        if (
            not prefix
            and Reimbursement.objects.filter(expenses__mission=mission_id).exclude(id__in=reimbursements_id).exists()
        ):
            prefix = '^'
        resource_data[f'{prefix}{mission.number}{suffix}'] = dict(
            zip(
                ['byexpcategory', 'bypayment', 'summary'],
                calculate_reimbursement_summaries(expenses_in_mr),
                strict=False,
            )
        )

    return results


@admin.register(Reimbursement)
class ReimbursementAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin):
    list_display = ['number', 'year', 'month', 'title', 'issue_date', 'paid_date', 'expense_num', 'resource']
    form = ReimbursementAdminForm
    inlines = [ExpenseInline]
    actions = ['report']
    autocomplete_fields = ['resource']
    search_fields = ['title', 'issue_date']
    list_filter = [
        'year',
        RecentFilter.factory('issue_date'),
        ('issue_date', DateRangeFilter),
        ('paid_date', admin.EmptyFieldListFilter),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Reimbursement]:
        return super().get_queryset(request).prefetch_related('expenses')

    def get_object(self, request: HttpRequest, object_id: int, from_field=None) -> Reimbursement:
        queryset = self.get_queryset(request)
        # Custom logic to retrieve the object
        return queryset.get(pk=object_id)

    def expense_num(self, obj: Reimbursement) -> int:
        return obj.expense_count

    expense_num.short_description = 'Num expenses'

    @button(
        html_attrs=NORMAL, visible=lambda btn: bool(Mission.objects.filter(expenses__reimbursement_id=btn.original.id))
    )
    def view_linked_missions(self, request: HttpRequest, pk: int) -> HttpResponse:
        rids = map(str, Mission.objects.filter(expenses__reimbursement_id=pk).values_list('id', flat=True))
        return redirect(reverse('admin:core_mission_changelist') + f"?id__in={','.join(rids)}&recent=False")

    @button(
        html_attrs=NORMAL,
    )
    def overview(self, request: HttpRequest, pk: int) -> TemplateResponse:
        reimbursement = self.get_object(request, pk)

        qs: QuerySet[Expense] = reimbursement.expenses.all()

        expenses = ReimbursementExpenseTable(qs, order_by=['day'])

        if export_format := request.GET.get('_export', None):
            expenses = ReimbursementExpenseExportTable(qs, order_by=['day'])
            return self.export_table(reimbursement, expenses, export_format, request)
        expenses = ReimbursementExpenseTable(qs, order_by=['day'])

        byexpcategory, bypayment, summary = calculate_reimbursement_summaries(qs)

        missions = {x.mission for x in qs}

        return TemplateResponse(
            request,
            context={
                'site_header': site.site_header,
                'reimbursement': reimbursement,
                'missions': missions,
                'expenses': expenses,
                'summary': summary,
                'payments': bypayment,
                'categories': byexpcategory,
                'base': settings.BASE_CURRENCY,
                'filename': format_html(f'{slugify(str(reimbursement))}.pdf'),
            },
            template='admin/missions/reimbursement/summary.html',
        )

    def export_table(
        self, reimbursement: Reimbursement, table_data: list, export_format: str, request: HttpRequest
    ) -> HttpResponse | None:
        """Export django table data."""
        from django_tables2.config import RequestConfig

        RequestConfig(request).configure(table_data)

        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table_data)
            return exporter.response(f'mission_{reimbursement.year}_{reimbursement.number}_expenses.{export_format}')
        return None

    @admin.action(description='Reimbursement report')
    def report(self, request: HttpRequest, queryset: QuerySet[Reimbursement]) -> TemplateResponse:
        """View reimbursement report."""
        context = {'data': prepare_reimbursement_report_context(queryset)}
        return TemplateResponse(
            request,
            'admin/missions/reimbursement/report.html',
            context=context,
        )
