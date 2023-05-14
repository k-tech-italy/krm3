from django.contrib import admin
from django.contrib.admin import ModelAdmin
from mptt.admin import MPTTModelAdmin

from krm3.missions.forms import MissionAdminForm
from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement


@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    form = MissionAdminForm


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(ModelAdmin):
    pass


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    pass


@admin.register(Expense)
class ExpenseAdmin(ModelAdmin):
    pass


@admin.register(Reimbursement)
class ReimbursementAdmin(ModelAdmin):
    pass
