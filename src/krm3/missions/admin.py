from django.contrib import admin
from django.contrib.admin import ModelAdmin

from krm3.missions.models import Mission


@admin.register(Mission)
class MissionAdmin(ModelAdmin):
    pass
