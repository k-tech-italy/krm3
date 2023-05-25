from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.template.response import TemplateResponse
from mptt.admin import MPTTModelAdmin

from krm3.missions.forms import MissionAdminForm
from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement


@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    form = MissionAdminForm


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(Expense)
class ExpenseAdmin(ExtraButtonsMixin, ModelAdmin):

    @button(
        html_attrs={'style': 'background-color:#DC6C6C;color:black'},
        visible=lambda btn: bool(btn.original.id)
    )
    def view_qr(self, request, pk):
        expense = self.model.objects.get(pk=pk)
        return TemplateResponse(
            request,
            context={'pk': pk, 'ref': f'{pk}-{expense.get_otp()}'},
            template='admin/missions/expense/expense_qr.html')


@admin.register(Reimbursement)
class ReimbursementAdmin(ModelAdmin):
    pass
