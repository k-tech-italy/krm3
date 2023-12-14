from django.contrib import admin
from django.contrib.admin import ModelAdmin
from smart_admin.smart_auth.admin import UserAdmin

from krm3.core.forms import ResourceAdminForm
from krm3.core.models import City, Client, Country, Project, Resource
from krm3.utils.queryset import ACLMixin

# from django.utils.html import escape
# from django.utils.safestring import mark_safe
#
# @admin.register(UserProfile)
# class UserProfileAdmin(ModelAdmin):
#     list_display = 'user', 'avatar', 'profile'
#
#     def avatar(self, obj):
#         if obj.picture:
#             return mark_safe('<img src="%s" />' % escape(obj.picture))
#         else:
#             return ''
#     avatar.short_description = 'Profile pic'
#     avatar.allow_tags = True
#
#     def profile(self, obj):
#
#         if obj.social_profile:
#             return mark_safe('<a href="%s">%s</a>' % (escape(obj.social_profile), escape(obj.social_profile)))
#         else:
#             return ''
#     avatar.short_description = 'Profile url'
#     avatar.allow_tags = True


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login', 'social_profile',
                    'picture')  # Added last_login


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
    search_fields = ['name']


@admin.register(Project)
class ProjectAdmin(ACLMixin, ModelAdmin):
    search_fields = ['name']
    autocomplete_fields = ['client']
