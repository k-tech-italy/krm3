
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.db.models import QuerySet
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.forms import RangeWidget
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from rangefilter.filters import DateRangeFilter

from krm3.core.models import PO, Basket, SpecialLeaveReason, TimeEntry, TimesheetSubmission, Resource
from krm3.styles.buttons import NORMAL
from django import forms


from django.utils.html import format_html

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

    def get_queryset(self, request: HttpRequest) -> QuerySet[TimeEntry]:
        qs = TimeEntry.objects.all()
        if request.user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return qs
        return qs.filter(resource__user=request.user)

    def has_view_permission(self,  request: HttpRequest, obj: TimeEntry | None = None) -> bool:
        if obj is None:
            return True
        if request.user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def has_change_permission(self, request: HttpRequest, obj: TimeEntry | None = None) -> bool:
        if obj is None:
            return True
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def has_delete_permission(self, request: HttpRequest, obj: TimeEntry | None = None) -> bool:
        if obj is None:
            return True
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return super().has_add_permission(request)

    def get_form(
            self,
            request: HttpRequest,
            obj: TimeEntry | None = None,
            **kwargs
    ) -> type[forms.ModelForm]:
        form = super().get_form(request, obj, **kwargs)

        is_add_view = obj is None
        user = request.user

        if not user.has_perm("core.manage_any_timesheet"):
            try:
                resource = Resource.objects.get(user=user)
                if is_add_view:
                    if "resource" in form.base_fields:
                        form.base_fields["resource"].queryset = Resource.objects.filter(pk=resource.pk)
                else:
                    pass
            except Resource.DoesNotExist:
                if is_add_view and "resource" in form.base_fields:
                    form.base_fields["resource"].queryset = Resource.objects.none()

        return form

    @button(html_attrs=NORMAL)
    def report(self, _request: HttpRequest) -> HttpResponseRedirect:
        return HttpResponseRedirect(reverse('report'))

    @button(html_attrs=NORMAL)
    def task_report(self, _request: HttpRequest) -> HttpResponseRedirect:
        return HttpResponseRedirect(reverse('task_report'))

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def goto_task(self, request: HttpRequest, pk: int) -> HttpResponseRedirect:
        obj = self.model.objects.get(pk=pk)
        return HttpResponseRedirect(reverse('admin:core_task_change', args=[obj.task_id]))

    @admin.display(description='Timesheet', ordering='timesheet')
    def get_timesheet(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_timesheetsubmission_change', args=[obj.timesheet_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.timesheet))

    @admin.display(description='Resource', ordering='resource')
    def get_resource(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_resource_change', args=[obj.resource_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.resource))

    @admin.display(description='Task', ordering='task')
    def get_task(self, obj: TimeEntry) -> str:
        url = reverse('admin:core_task_change', args=[obj.task_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.task))


@admin.register(SpecialLeaveReason)
class SpecialLeaveReasonAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description')
