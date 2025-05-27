from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from django.http import HttpRequest
from django.template.response import TemplateResponse

from krm3.core.models import PO, Basket, TimeEntry


@admin.register(PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


@admin.register(TimeEntry)
class TimeEntryAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_fields = ('date', 'resource', 'task', 'category', 'hours_worked', 'state')
    search_fields = ('date', 'category', 'state')
    list_filter = [('resource', AutoCompleteFilter), ('task', AutoCompleteFilter)]

    @button()
    def report(self, request: HttpRequest) -> TemplateResponse:
        if request.method == 'POST':
            return TemplateResponse(request, 'timesheet/report.html')
        return TemplateResponse(request, 'timesheet/report.html')
