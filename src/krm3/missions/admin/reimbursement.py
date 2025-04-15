import decimal
from decimal import Decimal

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.dates import DateRangeFilter
from adminfilters.mixin import AdminFiltersMixin
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import site
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django_tables2.export import TableExport

from krm3.missions.admin.expenses import ExpenseInline
from krm3.missions.forms import ReimbursementAdminForm
from krm3.core.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement
from krm3.missions.tables import ReimbursementExpenseExportTable, ReimbursementExpenseTable
from krm3.styles.buttons import NORMAL
from krm3.utils.queryset import ACLMixin


@admin.register(Reimbursement)
class ReimbursementAdmin(ACLMixin, ExtraButtonsMixin, AdminFiltersMixin):
    list_display = ['number', 'year', 'title', 'issue_date', 'paid_date', 'expense_num', 'resource']
    form = ReimbursementAdminForm
    inlines = [ExpenseInline]
    autocomplete_fields = ['resource']
    search_fields = ['title', 'issue_date']
    list_filter = [
        'year',
        ('issue_date', DateRangeFilter),
        ('paid_date', admin.EmptyFieldListFilter),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('expenses')

    # def get_queryset_(self, request):
    #     return Reimbursement.objects.prefetch_related('expenses').all()

    def get_object(self, request, object_id, from_field=None):
        queryset = self.get_queryset(request)
        # Custom logic to retrieve the object
        return queryset.get(pk=object_id)

    def expense_num(self, obj: Reimbursement):
        return obj.expense_count

    expense_num.short_description = 'Num expenses'

    @button(
        html_attrs=NORMAL,
        visible=lambda btn: bool(Mission.objects.filter(expenses__reimbursement_id=btn.original.id))
    )
    def view_linked_missions(self, request, pk):
        rids = map(str, Mission.objects.filter(expenses__reimbursement_id=pk).values_list('id', flat=True))
        return redirect(reverse('admin:core_mission_changelist') + f"?id__in={','.join(rids)}")

    @button(
        html_attrs=NORMAL,
    )
    def overview(self, request, pk):
        reimbursement = self.get_object(request, pk)

        qs = reimbursement.expenses.all()

        expenses = ReimbursementExpenseTable(qs, order_by=['day'])

        if export_format := request.GET.get('_export', None):
            expenses = ReimbursementExpenseExportTable(qs, order_by=['day'])
            return self.export_table(reimbursement, expenses, export_format, request)
        else:
            expenses = ReimbursementExpenseTable(qs, order_by=['day'])

        # categories = ExpenseCategory.objects.values_list('id', 'parent_id')

        bypayment = {pc: [decimal.Decimal(0)] * 2 for pc in PaymentCategory.objects.root_nodes()}
        byexpcategory = {pc: [decimal.Decimal(0)] * 2 for pc in ExpenseCategory.objects.root_nodes()}

        summary = {
                      'Totale spese': decimal.Decimal(0.0),
                      'Totale rimborso': decimal.Decimal(0.0),
                      'Non Rimborsate': decimal.Decimal(0.0),
                  } | {
                      expense.category.get_root(): decimal.Decimal(0.0)
                      for expense in qs
                  }
        for expense in qs:
            expense: Expense
            summary['Totale rimborso'] += expense.amount_reimbursement or decimal.Decimal(0.0)
            summary[expense.category.get_root()] += expense.amount_reimbursement or decimal.Decimal(0.0)

            bypayment[expense.payment_type.get_root()][0] += expense.amount_base or Decimal('0')
            bypayment[expense.payment_type.get_root()][1] += expense.amount_reimbursement or Decimal('0')

            byexpcategory[expense.category.get_root()][0] += expense.amount_base or Decimal('0')
            byexpcategory[expense.category.get_root()][1] += expense.amount_reimbursement or Decimal('0')
            summary['Non Rimborsate'] += (expense.amount_base or decimal.Decimal(0.0)) - (
                        expense.amount_reimbursement or decimal.Decimal(0.0)) \
                if expense.payment_type.personal_expense else decimal.Decimal(0.0)
            summary['Totale spese'] += (
                                           expense.amount_base if not expense.payment_type.personal_expense
                                           else expense.amount_reimbursement or Decimal('0')
                                       ) or decimal.Decimal(0.0)

        missions = set([x.mission for x in qs])

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
                'filename': format_html(f'{slugify(str(reimbursement))}.pdf')
            },
            template='admin/missions/reimbursement/summary.html')

    def export_table(self, reimbursement: Reimbursement, table_data, export_format, request):
        """Function to export django table data."""
        from django_tables2.config import RequestConfig

        RequestConfig(request).configure(table_data)

        if TableExport.is_valid_format(export_format):
            exporter = TableExport(export_format, table_data)
            return exporter.response(f'mission_{reimbursement.year}_{reimbursement.number}_expenses.{export_format}')
