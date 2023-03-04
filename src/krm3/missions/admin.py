from django.contrib import admin
from django.contrib.admin import ModelAdmin

from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement


@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    pass


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(ModelAdmin):
    pass


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(ModelAdmin):
    pass


@admin.register(Expense)
class ExpenseAdmin(ModelAdmin):
    pass


@admin.register(Reimbursement)
class ReimbursementAdmin(ModelAdmin):
    pass
