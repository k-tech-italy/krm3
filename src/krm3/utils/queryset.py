from adminfilters.autocomplete import AutoCompleteFilter
from django.contrib import admin
from django.db import models


class ACLMixin:
    """Restrict access to superuser, owner, or manager."""
    _resource_link = 'resource'

    def get_list_filter(self, request):
        ret = admin.ModelAdmin.get_list_filter(self, request).copy()
        if request.user.has_perm('missions.view_any_mission') or request.user.has_perm('missions.manage_any_mission'):
            ret.insert(1, (self._resource_link, AutoCompleteFilter),)
        return ret

    def get_queryset(self, request):
        return self.model.objects.filter_acl(request.user)

    def get_object(self, request, *args, **kwargs):
        ret = super().get_object(request, *args, **kwargs)
        if ret is None or not ret.is_accessible(request.user):
            raise self.model.DoesNotExist('Object does not exists or is unavailable')
        return ret


class ActiveQuerySet(models.QuerySet):
    def actives(self):
        return self.filter(active=True)


class ActiveManagerMixin:
    def active(self):
        return self.get_queryset().filter(active=True)
