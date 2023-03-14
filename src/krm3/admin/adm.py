import logging

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import site

import krm3
from krm3.core.models import City, Client, Country, Project, Resource, User

site.site_title = 'KRM3'
site.site_header = 'KRM3 admin console ' + krm3.__version__
site.enable_nav_sidebar = True


logger = logging.getLogger(__name__)


@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'last_login')  # Added last_login


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
