from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.forms import RangeWidget
from django.http import HttpRequest
from django.utils.html import format_html
from smart_admin.smart_auth.admin import UserAdmin

from krm3.core.forms import ContractForm
from krm3.core.models import City, Client, Contract, Country, ExtraHoliday, Resource, UserProfile, Contact, \
    AddressInfo, EmailInfo, PhoneInfo, WebsiteInfo, Website, Phone, Email, Address


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
    search_fields = ['name']


@admin.register(City)
class CityAdmin(AdminFiltersMixin, ModelAdmin):
    search_fields = ['name', 'country__name']
    list_filter = [('country__name', AutoCompleteFilter)]


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'active', 'preferred_in_report')
    search_fields = ['first_name', 'last_name']
    list_filter = (('active', admin.BooleanFieldListFilter),)


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    search_fields = ['name']


@admin.register(Contract)
class ContractAdmin(AdminFiltersMixin, ModelAdmin):
    form = ContractForm
    search_fields = ['user']
    list_display = [
        'resource',
        'get_period',
        'country_calendar_code',
        'working_schedule',
        'meal_voucher',
        'document_link',
    ]
    list_filter = [('resource', AutoCompleteFilter)]
    autocomplete_fields = ['resource']
    readonly_fields = ['document_link']

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


@admin.register(ExtraHoliday)
class ExtraHolidayAdmin(ModelAdmin):
    list_display = ('get_period', 'country_codes', 'reason')

    formfield_overrides = {
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: ExtraHoliday) -> str:
        return str(obj)


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

    @button(label="fetch photo")
    def fetch_picture(self, request: HttpRequest, contact_id: str) -> None:
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
