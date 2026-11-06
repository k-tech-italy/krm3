from __future__ import annotations

import datetime
import typing

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from concurrency.admin import ConcurrentModelAdmin
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.forms import RangeWidget
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.html import format_html
from smart_admin.smart_auth.admin import UserAdmin

from krm3.core.forms import ContractForm, ContractTerminationForm
from krm3.core.impexp import TimesheetExporter
from krm3.core.models import (
    Address,
    AddressInfo,
    City,
    Client,
    Contact,
    Contract,
    Country,
    Email,
    EmailInfo,
    ExtraHoliday,
    Phone,
    PhoneInfo,
    Resource,
    UserProfile,
    Website,
    WebsiteInfo,
)
from krm3.core.termination import ContractModifiedError, ContractTermination
from krm3.sentry import capture_exception
from krm3.styles.buttons import DANGEROUS, NORMAL

if typing.TYPE_CHECKING:
    from django.contrib.admin.options import _ModelT
    from django.db.models import QuerySet
    from django.http import HttpRequest


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = 'user', 'avatar', 'profile'

    def avatar(self, obj: UserProfile) -> str:
        if obj.picture:
            return format_html('<img src="{}" />', obj.picture)
        return ''

    avatar.short_description = 'Profile pic'
    avatar.allow_tags = True

    def profile(self, obj: UserProfile) -> str:
        if obj.social_profile:
            return format_html('<a href="{}">{}</a>', obj.social_profile, obj.social_profile)
        return ''

    avatar.short_description = 'Profile url'
    avatar.allow_tags = True


class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'is_staff',
        'last_login',
        'social_profile',
        'picture',
    )  # Added last_login
    list_filter = (('is_active', admin.BooleanFieldListFilter),)


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    search_fields = ['name', 'country_calendar_code']


@admin.register(City)
class CityAdmin(AdminFiltersMixin, ModelAdmin):
    search_fields = ['name', 'country__name', 'subdivision_code']
    list_filter = [('country__name', AutoCompleteFilter)]
    list_display = ('name', 'country', 'subdivision_code')


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    """Resource model admin."""

    list_display = ('first_name', 'last_name', 'user')
    search_fields = ['first_name', 'last_name']
    actions = ['export_timesheets']

    @admin.action(description='Export selected timesheets')
    def export_timesheets(self, request: 'HttpRequest', queryset: 'QuerySet[Resource]') -> 'JsonResponse':
        """Export selected timesheets."""
        try:
            buffer = TimesheetExporter(queryset).export()
            response = JsonResponse(buffer)
            now = datetime.now().strftime('%Y%m%d_%H%M%S')
            response['Content-Disposition'] = f'attachment; filename="mission-export-{now}.json"'
            # response['Content-Length'] = buffer.tell()  # noqa: ERA001

            return response
        except Exception as e:  # noqa: BLE001
            messages.error(request, f'Failed to export timesheets: {e}')
            capture_exception()


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    search_fields = ['name']


@admin.register(Contract)
class ContractAdmin(ExtraButtonsMixin, AdminFiltersMixin, ConcurrentModelAdmin):
    form = ContractForm
    search_fields = ['resource__last_name', 'resource__first_name', 'base_in__name']
    list_display = [
        'resource',
        'get_period',
        'contract_type',
        'base_in',
        'working_schedule',
        'holiday_day',
        'meal_voucher',
        'document_link',
    ]
    list_filter = [('resource', AutoCompleteFilter), ('base_in', AutoCompleteFilter)]
    autocomplete_fields = ['resource', 'base_in']
    readonly_fields = ['document_link']
    radio_fields = {'holiday_day': admin.HORIZONTAL}

    formfield_overrides = {
        # Tell Django to use our custom widget for all DateRangeFields in this admin.
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: Contract) -> str:
        return str(obj)

    @admin.display(description='Document')
    def document_link(self, obj: Contract) -> str:
        if obj.document_url:
            return format_html('<a href="{}">View document</a>', obj.document_url)
        return '-'

    @button(
        html_attrs=DANGEROUS,
        visible=lambda btn: not btn.original.period.upper,
        permission='core.change_contract',
    )
    def terminate(self, request: 'HttpRequest', pk: str) -> HttpResponse:
        """Ask for the termination date, list what the termination changes, and apply it once confirmed."""
        contract = get_object_or_404(Contract, pk=pk)
        if contract.period.upper:
            messages.error(request, 'The contract already has an end date.')
            return redirect('admin:core_contract_change', contract.pk)
        context = self.get_common_context(request, pk, title='Terminate Contract')

        if request.method == 'POST':
            form = ContractTerminationForm(request.POST, contract=contract)
            if form.is_valid():
                termination = ContractTermination(contract, form.cleaned_data['termination_date'])
                if 'confirm' in request.POST:
                    return self._apply_termination(request, termination, form.cleaned_data['version'])
                context.update(termination_preview(termination), form=form)
                return TemplateResponse(request, 'admin/core/contract/terminate_confirm.html', context)
        else:
            form = ContractTerminationForm(
                initial={'termination_date': datetime.date.today(), 'version': contract.version}, contract=contract
            )

        context['form'] = form
        return TemplateResponse(request, 'admin/core/contract/terminate.html', context)

    def _apply_termination(
        self, request: 'HttpRequest', termination: ContractTermination, version: int
    ) -> HttpResponse:
        try:
            outcome = termination.apply(version)
        except ContractModifiedError:
            messages.error(
                request,
                'Contract not terminated: it was changed after the termination was started. Review it and try again.',
            )
            return redirect('admin:core_contract_terminate', termination.contract.pk)
        except (ValidationError, ProtectedError) as e:
            messages.error(request, f'Contract not terminated: {"; ".join(getattr(e, "messages", [str(e)]))}')
            return redirect('admin:core_contract_change', termination.contract.pk)
        messages.success(
            request,
            f'Contract terminated on {termination.termination_date:%Y-%m-%d}.'
            f' Day entries deleted: {outcome.day_entries}.'
            f' Tasks deleted: {outcome.deleted_tasks}, truncated: {outcome.truncated_tasks}.'
            f' Timesheet submissions deleted: {outcome.deleted_submissions},'
            f' truncated: {outcome.truncated_submissions}.',
        )
        return redirect('admin:core_contract_changelist')


def termination_preview(termination: ContractTermination) -> dict[str, typing.Any]:
    """Return the template context listing what `termination` deletes or truncates.

    Periods are shown as (first day, last day), both included; the last day is None when the period is open.
    """

    def days(period: typing.Any) -> tuple[datetime.date, datetime.date | None]:
        return period.lower, period.upper - datetime.timedelta(days=1) if period.upper else None

    truncated_submissions = [(sub, *days(sub.period)) for sub in termination.truncated_submissions()]
    deleted_submissions = [(sub, *days(sub.period)) for sub in termination.deleted_submissions()]
    return {
        'termination_date': termination.termination_date,
        'day_entries': list(termination.day_entries().values_list('day', 'closed')),
        'deleted_tasks': [(task, *days(task.period)) for task in termination.deleted_tasks()],
        'truncated_tasks': [(task, *days(task.period)) for task in termination.truncated_tasks()],
        'truncated_submissions': truncated_submissions,
        'deleted_submissions': deleted_submissions,
        'submission_count': len(truncated_submissions) + len(deleted_submissions),
    }


@admin.register(ExtraHoliday)
class ExtraHolidayAdmin(ExtraButtonsMixin, ModelAdmin):
    """Extra Holidays are deprecated until further development."""

    list_display = ('get_period', 'country_codes', 'reason')

    formfield_overrides = {
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: ExtraHoliday) -> str:
        return str(obj)

    @button(html_attrs=NORMAL, label='Reset resolve cache')
    def reset_resolve_cache(self, request: 'HttpRequest') -> None:
        # extra_holidays.clear()  # noqa: ERA001
        messages.success(request, 'ExtraHoliday resolve cache has been reset.')

    def has_delete_permission(self, request: HttpRequest, obj: _ModelT | None = ...) -> bool:
        return False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: _ModelT | None = ...) -> bool:
        return False


class WebsiteInfoInline(admin.TabularInline):
    model = WebsiteInfo
    extra = 1


class PhoneInfoInline(admin.TabularInline):
    model = PhoneInfo
    extra = 1


class EmailInfoInline(admin.TabularInline):
    model = EmailInfo
    extra = 1


class AddressInfoInline(admin.TabularInline):
    model = AddressInfo
    extra = 1


@admin.register(Contact)
class ContactAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'job_title', 'is_active')
    search_fields = ('first_name', 'last_name', 'tax_id')
    inlines = [
        WebsiteInfoInline,
        PhoneInfoInline,
        EmailInfoInline,
        AddressInfoInline,
    ]

    @button(label='fetch photo')
    def fetch_picture(self, request: 'HttpRequest', contact_id: str) -> None:
        Contact.objects.get(pk=contact_id).fetch_picture()


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('url',)


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number',)


@admin.register(Email)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('address',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('address',)
