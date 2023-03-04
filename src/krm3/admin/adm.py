import logging

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import site
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

import krm3
from krm3.models import City, Client, Country, Project, Resource

site.site_title = 'KRM3'
site.site_header = 'KRM3 admin console ' + krm3.__version__
site.enable_nav_sidebar = True


logger = logging.getLogger(__name__)


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login')  # Added last_login


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    pass


@admin.register(City)
class CityAdmin(ModelAdmin):
    pass


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    pass


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    pass


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
