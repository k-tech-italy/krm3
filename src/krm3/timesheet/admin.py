from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin

from krm3.core.models import PO, Basket, TimeEntry


@admin.register(PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


@admin.register(TimeEntry)
class TimeEntryAdmin(AdminFiltersMixin, admin.ModelAdmin):
    list_fields = ('date', 'resource', 'task', 'category', 'hours_worked', 'state')
    search_fields = ('date', 'category', 'state')
    list_filter = [('resource', AutoCompleteFilter), ('task', AutoCompleteFilter)]
