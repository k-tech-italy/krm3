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

    def render_amount_currency(self, record: Expense) -> str:

        value = f'{record.amount_currency} {record.currency.iso3}'
        return mark_safe(value)  # noqa: S308

    @classmethod
    def render_amount_base(cls, value: Decimal) -> Decimal | str:
        if getattr(cls, 'export', False) is True:
            return value
        if value and value < decimal.Decimal(0):
            value = f'{value} {settings.BASE_CURRENCY}'
            return mark_safe('<span style="color: red;">%s</span>' % value)  # noqa: S308
        return f'{value} {settings.BASE_CURRENCY}'

    @classmethod
    def render_amount_reimbursement(cls, value: Decimal) -> Decimal | str:
        if getattr(cls, 'export', False) is True:
            return value
        if value and value < decimal.Decimal(0):
            return mark_safe('<span style="color: red;">%s</span>' % value)  # noqa: S308
        return value

    def render_day(self, value: datetime.date) -> str:
        return datetime.strftime(value, '%Y-%m-%d')

    def render_attachment(self, record: Expense) -> str:
        if record.image:
            return self.render_image(record.image)
        url = reverse('admin:core_expense_changelist')
        return mark_safe(f'<a href="{url}{record.id}/view_qr/">--</a>')  # noqa: S308


class MissionExpenseBaseTable(ExpenseTableMixin, tables.Table):
    id = tables.Column(footer='Totals')
    amount_base = tables.Column(
        footer=lambda table: sum(x.amount_base or Decimal(0.0) for x in table.data)
    )
    amount_reimbursement = tables.Column(
        footer=lambda table: sum(x.amount_reimbursement or Decimal(0.0) for x in table.data)
    )


class MissionExpenseTable(MissionExpenseBaseTable):

    def render_image(self, record: Expense) -> str:
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')  # noqa: S308
        return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')  # noqa: S308

    def render_reimbursement(self, record: Expense) -> str:
        if record.reimbursement:
            url = reverse('admin:core_reimbursement_change', args=[record.reimbursement.id])
            return mark_safe(f'<a href="{url}">{record.reimbursement}</a>')  # noqa: S308
        return '--'

    def render_id(self, value: int) -> str:
        url = reverse('admin:core_expense_change', args=[value])
        return mark_safe(f'<a href="{url}">{value}</a>')  # noqa: S308

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'currency', 'reimbursement')

class MissionExpenseExportTable(MissionExpenseBaseTable):
    export = True

    def render_image(self, record: Expense) -> str:
        return 'yes' if record.image else 'no'

    def render_reimbursement(self, record: Expense) -> str:
        return record.reimbursement if record.reimbursement else '--'

    class Meta:
        model = Expense
        exclude = ('mission', 'created_ts', 'modified_ts', 'currency')

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


class ReimbursementExpenseTable(ReimbursementExpenseBaseTable):

    def render_id(self, record: Expense) -> str:
        url = reverse('admin:core_expense_change', args=[record.id])
        return mark_safe(f'<a href="{url}">{record.id}</a>')  # noqa: S308

    def render_image(self, record: Expense) -> str:
        if record.image:
            return mark_safe(f'<a href="{record.image.url}"><img src="{static("admin/img/icon-yes.svg")}"></a>')  # noqa: S308
        return mark_safe(f'<img src="{static("admin/img/icon-no.svg")}">')  # noqa: S308

    def render_mission(self, record: Expense) -> str:
        if record.mission:
            url = reverse('admin:core_mission_change', args=[record.mission.id])
            return mark_safe(f'<a href="{url}">{record.mission}</a>')  # noqa: S308
        return '--'


class ReimbursementExpenseExportTable(ReimbursementExpenseBaseTable):
    export = True

    def render_image(self, record: Expense) -> str:
        return 'yes' if record.image else 'no'

    def render_mission(self, record: Expense) -> str:
        return record.mission if record.mission else '--'
