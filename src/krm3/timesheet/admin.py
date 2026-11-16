from collections.abc import Sequence

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from adminfilters.num import NumberFilter
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.forms import RangeWidget
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from rangefilter.filters import DateRangeFilter

from krm3.core.models import PO, Basket, DayEntry, SpecialLeaveReason, TaskEntry, TimesheetSubmission
from krm3.daterange import DateRangeOverlapFilter
from krm3.events.notifications.timesheets import TimesheetApprovedNotification, TimesheetRejectedNotification
from krm3.styles.buttons import NORMAL


@admin.register(PO)
class POAdmin(AdminFiltersMixin, admin.ModelAdmin):
    search_fields = ('ref', 'state', 'project')
    list_filter = [('project', AutoCompleteFilter)]

    formfield_overrides = {
        # Tell Django to use our custom widget for all DateRangeFields in this admin.
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    search_fields = ('title',)


class TimesheetRejectionForm(forms.Form):
    message = forms.CharField(label='Rejection message', widget=forms.Textarea, required=True)


@admin.register(TimesheetSubmission)
class TimesheetSubmissionAdmin(ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    list_display = ('get_period', 'resource', 'status')
    list_filter = [
        ('resource', AutoCompleteFilter),
        ('period', DateRangeOverlapFilter),
        'status',
    ]

    formfield_overrides = {
        # Tell Django to use our custom widget for all DateRangeFields in this admin.
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_staff and request.user.has_perm('core.manage_any_timesheet')

    def has_change_permission(self, request: HttpRequest, obj: TimesheetSubmission | None = None) -> bool:
        return self.has_module_permission(request)

    def _transition(
        self,
        submission: TimesheetSubmission,
        status: str,
        rejection_message: str = '',
    ) -> None:
        with transaction.atomic():
            submission.status = status
            submission.rejection_message = rejection_message
            submission.save(update_fields=('status', 'timesheet', 'rejection_message'))
            if status == TimesheetSubmission.Status.CLOSED:
                transaction.on_commit(lambda: TimesheetApprovedNotification()(submission))
            elif status == TimesheetSubmission.Status.REJECTED:
                transaction.on_commit(lambda: TimesheetRejectedNotification()(submission))

    def _get_submission(self, request: HttpRequest, pk: int) -> TimesheetSubmission:
        return self.get_queryset(request).get(pk=pk)

    @button(html_attrs=NORMAL, visible=lambda btn: btn.original.status == TimesheetSubmission.Status.PENDING)
    def approve(self, request: HttpRequest, pk: int) -> HttpResponseRedirect:
        submission = self._get_submission(request, pk)
        if submission.status != TimesheetSubmission.Status.PENDING:
            self.message_user(request, 'Only pending submissions can be approved.', messages.ERROR)
        else:
            self._transition(submission, TimesheetSubmission.Status.CLOSED)
            self.message_user(request, 'Timesheet submission approved.', messages.SUCCESS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '.'))

    @button(html_attrs=NORMAL, visible=lambda btn: btn.original.status == TimesheetSubmission.Status.CLOSED)
    def reopen(self, request: HttpRequest, pk: int) -> HttpResponseRedirect:
        submission = self._get_submission(request, pk)
        if submission.status != TimesheetSubmission.Status.CLOSED:
            self.message_user(request, 'Only closed submissions can be reopened.', messages.ERROR)
        else:
            try:
                self._transition(submission, TimesheetSubmission.Status.DRAFT)
            except ValidationError as exc:
                self.message_user(request, str(exc), messages.ERROR)
            else:
                self.message_user(request, 'Timesheet submission reopened.', messages.SUCCESS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '.'))

    @button(html_attrs=NORMAL, visible=lambda btn: btn.original.status == TimesheetSubmission.Status.PENDING)
    def reject(self, request: HttpRequest, pk: int) -> HttpResponse:
        submission = self._get_submission(request, pk)
        if submission.status != TimesheetSubmission.Status.PENDING:
            self.message_user(request, 'Only pending submissions can be rejected.', messages.ERROR)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '.'))
        if request.method == 'POST':
            form = TimesheetRejectionForm(request.POST)
            if form.is_valid():
                self._transition(
                    submission,
                    TimesheetSubmission.Status.REJECTED,
                    rejection_message=form.cleaned_data['message'],
                )
                self.message_user(request, 'Timesheet submission rejected.', messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:core_timesheetsubmission_change', args=[submission.pk]))
        else:
            form = TimesheetRejectionForm()
        return TemplateResponse(
            request,
            'admin/core/timesheetsubmission/reject.html',
            {'form': form, 'submission': submission, 'opts': self.model._meta},
        )

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: TimesheetSubmission) -> str:
        return str(obj)

    @button(html_attrs=NORMAL, visible=lambda btn: bool(btn.original.id))
    def view_entries(self, request: 'HttpRequest', pk: int) -> HttpResponseRedirect:
        url = reverse('admin:core_taskentry_changelist') + f'?day_entry__timesheet_id={pk}'
        return HttpResponseRedirect(url)


class ResourceAdminMixin:
    @admin.display(description='Resource', ordering='resource')
    def get_resource(self, obj: TaskEntry) -> str:
        resource = self._resource_accessor(obj)
        url = reverse('admin:core_resource_change', args=[resource.id])
        return format_html('<a href="{}">{}</a>', url, str(resource))


@admin.register(DayEntry)
class DayEntryAdmin(ResourceAdminMixin, ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    _resource_accessor = lambda adminmodel, obj: obj.resource

    list_display = ('day', 'get_resource', 'asked_holiday', 'is_sick')

    list_filter = [
        ('resource', AutoCompleteFilter),
        ('day', DateRangeFilter),
        ('special_leave_hours', NumberFilter),
        ('rest_hours', NumberFilter),
        ('leave_hours', NumberFilter),
        'asked_holiday',
        ('bank', NumberFilter),
    ]
    list_select_related = ('resource', 'timesheet')
    calculated_fields = (
        'closed',
        'timesheet',
        'due_hours',
        'is_holiday',
        'day_hours',
        'night_hours',
        'travel_hours',
        'on_call_hours',
        'overtime_hours',
        'meal_voucher_threshold',
        'meal_voucher',
    )

    def get_readonly_fields(self, request: HttpRequest, obj: DayEntry | None = None) -> Sequence[str]:
        readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_superuser:
            return readonly_fields
        if obj is not None:
            readonly_fields = (*readonly_fields, 'resource', 'contract')
        return (*readonly_fields, *self.calculated_fields)

    def get_queryset(self, request: HttpRequest) -> QuerySet[TaskEntry]:
        qs = DayEntry.objects.all()
        if request.user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return qs
        return qs.filter(resource__user=request.user)

    def has_view_permission(self, request: HttpRequest, obj: DayEntry | None = None) -> bool:
        if obj is None:
            return True
        if request.user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def has_change_permission(self, request: HttpRequest, obj: DayEntry | None = None) -> bool:
        if obj is None:
            return True
        if obj.is_submitted:
            return False
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def has_delete_permission(self, request: HttpRequest, obj: DayEntry | None = None) -> bool:
        if obj is None:
            return True
        if obj.is_submitted:
            return False
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return obj.resource.user == request.user

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[DayEntry]) -> None:
        if queryset.submitted().exists():
            self.message_user(
                request,
                'Closed time entries cannot be deleted. Reopen the timesheet first.',
                level=messages.ERROR,
            )
            return
        super().delete_queryset(request, queryset)

    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.has_perm('core.manage_any_timesheet'):
            return True
        return super().has_add_permission(request)


@admin.register(TaskEntry)
class TaskEntryAdmin(ResourceAdminMixin, ExtraButtonsMixin, AdminFiltersMixin, admin.ModelAdmin):
    _resource_accessor = lambda adminmodel, obj: obj.day_entry.resource

    list_display = ('id', 'get_day', 'get_resource', 'get_task')

    list_filter = [
        ('task__project', AutoCompleteFilter),
        ('day_entry__resource', AutoCompleteFilter),
        ('task', AutoCompleteFilter),
        ('day_entry__day', DateRangeFilter),
        ('day_shift_hours', NumberFilter),
        ('night_shift_hours', NumberFilter),
        ('travel_hours', NumberFilter),
        ('on_call_hours', NumberFilter),
    ]
    list_select_related = ('task__project', 'day_entry__resource', 'day_entry__timesheet')

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[TaskEntry]':
        requestor = request.user
        qs = super().get_queryset(request).select_related('day_entry')
        if not requestor.has_any_perm('core.view_any_timesheet', 'core.manage_any_timesheet'):
            qs = qs.filter(day_entry__resource__user=requestor)
        return qs

    def lookup_allowed(self, lookup: str, value: str, request: HttpRequest | None = None) -> bool:
        if lookup == 'day_entry__timesheet_id':
            return True
        return super().lookup_allowed(lookup, value, request)

    def has_change_permission(self, request: HttpRequest, obj: TaskEntry | None = None) -> bool:
        if obj is not None and obj.is_submitted:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: TaskEntry | None = None) -> bool:
        if obj is not None and obj.is_submitted:
            return False
        return super().has_delete_permission(request, obj)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[TaskEntry]) -> None:
        if queryset.submitted().exists():
            self.message_user(
                request,
                'Closed time entries cannot be deleted. Reopen the timesheet first.',
                level=messages.ERROR,
            )
            return
        super().delete_queryset(request, queryset)

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

    @admin.display(description='DayEntry', ordering='day_entry')
    def get_day(self, obj: TaskEntry) -> str:
        url = reverse('admin:core_dayentry_change', args=[obj.day_entry_id])
        return format_html('<a href="{}">{}</a>', url, obj.day_entry.day.strftime('%Y-%m-%d'))

    @admin.display(description='Timesheet', ordering='timesheet')
    def get_timesheet(self, obj: TaskEntry) -> str:
        url = reverse('admin:core_timesheetsubmission_change', args=[obj.day_entry.timesheet_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.day_entry.timesheet))

    @admin.display(description='Task', ordering='task')
    def get_task(self, obj: TaskEntry) -> str:
        url = reverse('admin:core_task_change', args=[obj.task_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.task))


@admin.register(SpecialLeaveReason)
class SpecialLeaveReasonAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description')
