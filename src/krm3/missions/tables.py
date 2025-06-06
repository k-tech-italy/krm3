import decimal
from datetime import datetime
from decimal import Decimal

import django_tables2 as tables
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from krm3.core.models import Expense


class ExpenseTableMixin:
    attachment = tables.Column(empty_values=())

    def render_amount_currency(self, record):

        value = f'{record.amount_currency} {record.currency.iso3}'
        return mark_safe(value)

    def render_amount_base(self, value):
        if value:
            if value < decimal.Decimal(0):
                value = f'{value} {settings.BASE_CURRENCY}'
                return mark_safe('<span style="color: red;">%s</span>' % value)
        return f'{value} {settings.BASE_CURRENCY}'

    def render_amount_reimbursement(self, value):
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)
        return value

    def render_day(self, value):
        return datetime.strftime(value, '%Y-%m-%d')

    def render_image(self, value):
        file_type = value.name.split('.')[-1]
        # url = reverse('admin:core_expense_change', args=[value])
        return mark_safe(f'<a href="{value.url}">{file_type}</a>')

    def render_attachment(self, record):
        if record.image:
            return self.render_image(record.image)
        else:
            url = reverse('admin:core_expense_changelist')
            return mark_safe(f'<a href="{url}{record.id}/view_qr/">--</a>')


class MissionExpenseBaseTable(ExpenseTableMixin, tables.Table):
    id = tables.Column(footer='Totals')
    amount_base = tables.Column(
        footer=lambda table: sum(x.amount_base or Decimal(0.0) for x in table.data)
    )
    amount_reimbursement = tables.Column(
        footer=lambda table: sum(x.amount_reimbursement or Decimal(0.0) for x in table.data)
    )

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'currency')


class MissionExpenseTable(MissionExpenseBaseTable):

    def render_image(self, record):
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')
        else:
            return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')

    def render_reimbursement(self, record):
        if record.reimbursement:
            url = reverse('admin:core_reimbursement_change', args=[record.reimbursement.id])
            return mark_safe(f'<a href="{url}">{record.reimbursement}</a>')
        else:
            return '--'

    def render_id(self, value):
        url = reverse('admin:core_expense_change', args=[value])
        return mark_safe(f'<a href="{url}">{value}</a>')


class MissionExpenseExportTable(MissionExpenseBaseTable):

    def render_image(self, record):
        return 'yes' if record.image else 'no'

    def render_reimbursement(self, record):
        return record.reimbursement if record.reimbursement else '--'


class ReimbursementExpenseBaseTable(ExpenseTableMixin, tables.Table):
    id = tables.Column(footer='Totals')
    amount_base = tables.Column(
        footer=lambda table: sum(x.amount_base or Decimal(0.0) for x in table.data)
    )
    amount_reimbursement = tables.Column(
        footer=lambda table: sum(x.amount_reimbursement or Decimal(0.0) for x in table.data)
    )

    class Meta:
        model = Expense
        exclude = ('reimbursement', 'created_ts', 'modified_ts', 'currency')

    def render_id(self, record):
        url = reverse('admin:core_expense_change', args=[record.id])
        return mark_safe(f'<a href="{url}">{record.id}</a>')


class ReimbursementExpenseTable(ReimbursementExpenseBaseTable):
    def render_image(self, record):
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')
        else:
            return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')

    def render_mission(self, record):
        if record.mission:
            url = reverse('admin:core_mission_change', args=[record.mission.id])
            return mark_safe(f'<a href="{url}">{record.mission}</a>')
        else:
            return '--'


class ReimbursementExpenseExportTable(ReimbursementExpenseBaseTable):
    def render_image(self, record):
        return 'yes' if record.image else 'no'

    def render_mission(self, record):
        return record.mission if record.mission else '--'
