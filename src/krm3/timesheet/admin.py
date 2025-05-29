from decimal import Decimal as D

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from django.http import HttpRequest
from django.template.response import TemplateResponse

from krm3.core.models import PO, Basket, Resource, SpecialLeaveReason, TimeEntry


@admin.register(PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


def _base_data():
    return {
        'day_shift': [D('0.00'), D('12.50'), D('0.00'), D('0.00'), D('4.00'), D('0.00'), D('0.00'), D('0.00')],
        'night_shift': [D('0.00'), D('2.50'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'on_call': [D('0.00'), D('0.00'), D('0.00'), D('1.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'travel': [D('0.00'), D('2.00'), D('0.00'), D('2.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'holiday': [D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'leave': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('1.50'), D('0.00'), D('0.00')],
        'rest': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'special_leave|1': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.50'), D('0.00')],
        'special_leave|2': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('5.0')],
        'sick': [D('0.00'), D('0.00'), D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'overtime': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    }


def get_fake_data():
    return {
        f'{r.last_name}, {r.first_name}': _base_data()
        for r in Resource.objects.order_by('last_name', 'first_name').all()
    }


@admin.register(TimeEntry)
class TimeEntryAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_fields = ('date', 'resource', 'task', 'category', 'hours_worked', 'state')
    search_fields = ('date', 'category', 'state')
    list_filter = [('resource', AutoCompleteFilter), ('task', AutoCompleteFilter)]

    @button()
    def report(self, request: HttpRequest) -> TemplateResponse:
        ctx = {
            'prev_month': '202503',
            'next_month': '202505',
            'title': 'April 2025',
            'data': get_fake_data(),  # TODO
        }
        return TemplateResponse(request, 'timesheet/report.html', context=ctx)


@admin.register(SpecialLeaveReason)
class SpecialLeaveReasonAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description')
