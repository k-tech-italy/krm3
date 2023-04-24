import logging

from django.contrib import admin
from django.contrib.admin.sites import site

import krm3
from krm3.core.admin import CustomUserAdmin
from krm3.core.models import User

site.site_title = 'KRM3'
site.site_header = 'KRM3 admin console ' + krm3.__version__
site.enable_nav_sidebar = True


logger = logging.getLogger(__name__)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
