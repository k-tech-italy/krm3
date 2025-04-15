from django.contrib import admin

from krm3.core.models import Invoice, InvoiceEntry


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin): ...


@admin.register(InvoiceEntry)
class InvoiceEntryAdmin(admin.ModelAdmin):
    search_fields = ('invoice',)
