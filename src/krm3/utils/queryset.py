from __future__ import annotations
import typing

from adminfilters.autocomplete import AutoCompleteFilter
from django.contrib import admin
from django.db import models

if typing.TYPE_CHECKING:
    from django.http import HttpRequest


class ACLMixin:
    """Restrict access to superuser, owner, or manager."""

    _resource_link = 'resource'

    def get_list_filter(self, request: HttpRequest):  # noqa: ANN001, ANN201
        ret = admin.ModelAdmin.get_list_filter(self, request).copy()
        if request.user.has_any_perm(*self.acl_permissions):
            ret.insert(
                1,
                (self._resource_link, AutoCompleteFilter),
            )
        return ret

    def get_queryset(self, request: HttpRequest):  # noqa: ANN001, ANN201
        return self.model.objects.filter_acl(request.user)

    def get_object(self, request: HttpRequest, *args, **kwargs):  # noqa: ANN001, ANN201
        ret = super().get_object(request, *args, **kwargs)
        if ret is None or not ret.is_accessible(request.user):
            raise self.model.DoesNotExist('Object does not exists or is unavailable')
        return ret


class ActiveQuerySet(models.QuerySet):
    def actives(self):  # noqa: ANN201
        return self.filter(active=True)
