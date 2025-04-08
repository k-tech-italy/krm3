from django.contrib import admin

from krm3.accounting import models as accounting_models


@admin.register(accounting_models.Invoice)
class InvoiceAdmin(admin.ModelAdmin): ...


@admin.register(accounting_models.InvoiceEntry)
class InvoiceEntryAdmin(admin.ModelAdmin):
    search_fields = ('invoice',)
