
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.mixin import AdminFiltersMixin
from django.contrib import admin
from django.contrib.postgres.fields import DateRangeField
from django.db.models import JSONField
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.postgres.forms import RangeWidget
from django.contrib.admin import ModelAdmin
from smart_admin.smart_auth.admin import UserAdmin

from krm3.core.models import City, Client, Country, Resource, UserProfile, Contract, ExtraHoliday

from django.utils.html import escape
from django.utils.safestring import mark_safe

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = 'user', 'avatar', 'profile'

    def avatar(self, obj: UserProfile) -> str:
        if obj.picture:
            return mark_safe('<img src="%s" />' % escape(obj.picture))  # noqa: S308
        return ''
    avatar.short_description = 'Profile pic'
    avatar.allow_tags = True

    def profile(self, obj: UserProfile) -> str:
        if obj.social_profile:
            return mark_safe('<a href="%s">%s</a>' % (escape(obj.social_profile), escape(obj.social_profile)))  # noqa: S308
        return ''
    avatar.short_description = 'Profile url'
    avatar.allow_tags = True


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'last_login',
                    'social_profile', 'picture')  # Added last_login
    list_filter = (
        ('is_active', admin.BooleanFieldListFilter),
    )


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    search_fields = ['name']


@admin.register(City)
class CityAdmin(AdminFiltersMixin, ModelAdmin):
    search_fields = ['name', 'country__name']
    list_filter = [
        ('country__name', AutoCompleteFilter)
    ]


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    list_display = ('first_name', 'last_name', 'user')
    search_fields = ['first_name', 'last_name']


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    search_fields = ['name']


@admin.register(Contract)
class ContractAdmin(ModelAdmin):
    search_fields = ['user']

    formfield_overrides = {
        # Tell Django to use our custom widget for all DateRangeFields in this admin.
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
        JSONField: {
            'help_text': '{"mon": 8, "tue": 8, "wed": 8, "thu": 8, "fri": 8, "sat": 0, "sun": 0}'
        }
    }

@admin.register(ExtraHoliday)
class ExtraHolidayAdmin(ModelAdmin):
    list_display = ('get_period', 'country_codes', 'reason')

    formfield_overrides = {
        DateRangeField: {'widget': RangeWidget(base_widget=AdminDateWidget)},
    }

    @admin.display(description='Period', ordering='period')
    def get_period(self, obj: ExtraHoliday) -> str:
        return str(obj)
