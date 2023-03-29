from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.utils.safestring import mark_safe

from krm3.core.models import UserProfile


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
