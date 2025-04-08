from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin

from krm3.timesheet import models as timesheet_models


@admin.register(timesheet_models.PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]


@admin.register(timesheet_models.Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


@admin.register(timesheet_models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_fields = ('title', 'project', 'resource', 'basket_title')
    search_fields = ('title', 'project', 'resource', 'basket_title')


@admin.register(timesheet_models.TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_fields = ('date', 'resource', 'task', 'category', 'hours_worked', 'state')
    search_fields = ('date', 'category', 'state')
    list_filter = [('resource', AutoCompleteFilter), ('task', AutoCompleteFilter)]
