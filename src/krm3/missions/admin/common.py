from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from krm3.core.models import DocumentType, ExpenseCategory, PaymentCategory


@admin.register(DocumentType)
class DocumentTypeAdmin(ExtraButtonsMixin, AdminFiltersMixin):
    list_display = ['title', 'active', 'default']
    search_fields = ['title']


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(MPTTModelAdmin):
    list_display = ['title', 'active', 'personal_expense']
    search_fields = ['title']
    autocomplete_fields = ['parent']
    list_filter = ['personal_expense']


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(MPTTModelAdmin):
    list_display = ['title', 'active']
    search_fields = ['title']
    autocomplete_fields = ['parent']
