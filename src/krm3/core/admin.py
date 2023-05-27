from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.safestring import mark_safe
from smart_admin.smart_auth.admin import UserAdmin

from krm3.core.forms import ResourceAdminForm
from krm3.core.models import City, Client, Country, Project, Resource, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = 'user', 'avatar'

    def avatar(self, obj):
        from django.utils.html import escape
        if obj.picture:
            return mark_safe('<img src="%s" />' % escape(obj.picture))
        else:
            return ''
    avatar.short_description = 'Profile pic'
    avatar.allow_tags = True


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login')  # Added last_login


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    search_fields = ['name']


@admin.register(City)
class CityAdmin(ModelAdmin):
    search_fields = ['name', 'country__name']


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    list_display = ('first_name', 'last_name')
    search_fields = ('first_name', 'last_name')
    form = ResourceAdminForm


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    search_fields = ['name']
