from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.forms import RangeWidget
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from rangefilter.filters import DateRangeFilter

from krm3.core.models import PO, Basket, SpecialLeaveReason, TimeEntry, TimesheetSubmission
from krm3.styles.buttons import NORMAL
from krm3.timesheet.report import timesheet_report_data

@admin.register(PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


@admin.register(TimesheetSubmission)
class TimesheetSubmissionAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_display = ('get_period', 'resource', 'closed')
    list_filter = [('resource', AutoCompleteFilter)]

    formfield_overrides = {
        # Tell Django to use our custom widget for all DateRangeFields in this admin.
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: TimesheetSubmission) -> str:
        return str(obj)

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def view_entries(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        url = reverse('admin:core_timeentry_changelist') + f'?timesheet_id={pk}'
        return HttpResponseRedirect(url)

@admin.register(TimeEntry)
class TimeEntryAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_display = ('date', 'get_resource', 'get_task', 'get_timesheet')
    search_fields = ('date', 'category')

    list_filter = [
        ('resource', AutoCompleteFilter),
        ('task', AutoCompleteFilter),
        ('date', DateRangeFilter),
    ]
    list_select_related = ('task__project', 'resource', 'timesheet')

    @button()
    def report(self, request: HttpRequest) -> TemplateResponse:
        current_month = request.GET.get('month')
        ctx = timesheet_report_data(current_month)
        return TemplateResponse(request, 'timesheet/report.html', context=ctx)

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_task(self, request: HttpRequest, pk: int) -> HttpResponseRedirect:
        obj = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_task_change', args=[obj.task_id]))

    @admin.display(description='Timesheet', ordering='timesheet')
    def get_timesheet(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_timesheetsubmission_change', args=[obj.timesheet_id])
        txt = f'<a href="{url}">{str(obj.timesheet)}</a>'
        return mark_safe(txt)  # noqa: S308

    @admin.display(description='Resource', ordering='resource')
    def get_resource(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_resource_change', args=[obj.resource_id])
        txt = f'<a href="{url}">{str(obj.resource)}</a>'
        return mark_safe(txt)  # noqa: S308

    @admin.display(description='Task', ordering='task')
    def get_task(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_task_change', args=[obj.task_id])
        txt = f'<a href="{url}">{str(obj.task)}</a>'
        return mark_safe(txt)  # noqa: S308


@admin.register(SpecialLeaveReason)
class SpecialLeaveReasonAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description')
