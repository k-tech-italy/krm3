import decimal
from datetime import datetime

import django_tables2 as tables
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from krm3.missions.models import Expense


class ExpenseTableMixin:
    attachment = tables.Column(empty_values=())

    def render_amount_currency(self, record):

        if record.payment_type.personal_expense:
            value = f'<span style="color: blue;">{record.amount_currency} {record.currency.iso3}</span>'
        else:
            value = f'{record.amount_currency} {record.currency.iso3}'
        return mark_safe(value)

    def render_amount_base(self, value):
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)
        return value

    def render_amount_reimbursement(self, value):
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)
        return value

    def render_day(self, value):
        return datetime.strftime(value, '%Y-%m-%d')

    def render_id(self, value):
        url = reverse('admin:missions_expense_change', args=[value])
        return mark_safe(f'<a href="{url}">{value}</a>')

    def render_image(self, value):
        file_type = value.name.split('.')[-1]
        # url = reverse('admin:missions_expense_change', args=[value])
        return mark_safe(f'<a href="{value.url}">{file_type}</a>')

    def render_attachment(self, record):
        if record.image:
            return self.render_image(record.image)
        else:
            url = reverse('admin:missions_expense_changelist')
            return mark_safe(f'<a href="{url}{record.id}/view_qr/">--</a>')


class MissionExpenseTable(ExpenseTableMixin, tables.Table):
    def render_image(self, record):
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')
        else:
            return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')

    def render_reimbursement(self, record):
        if record.reimbursement:
            url = reverse('admin:missions_reimbursement_change', args=[record.reimbursement.id])
            return mark_safe(f'<a href="{url}">{record.reimbursement}</a>')
        else:
            return '--'

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'currency')


class ReimbursementExpenseTable(ExpenseTableMixin, tables.Table):
    def render_image(self, record):
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')
        else:
            return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')

    def render_mission(self, record):
        if record.mission:
            url = reverse('admin:missions_mission_change', args=[record.mission.id])
            return mark_safe(f'<a href="{url}">{record.mission}</a>')
        else:
            return '--'

    class Meta:
        model = Expense
        exclude = ('reimbursement', 'created_ts', 'modified_ts', 'currency')
