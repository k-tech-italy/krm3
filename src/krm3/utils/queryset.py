from django.db import models
#
# def filter_for_resource(request, queryset, lookup='resource'):
#     if not request.user.is_superuser:
#         queryset = queryset.filter(**{lookup: request.user.profile.resource})
#     return queryset
#
#
# class FilterByResourceMixin:
#     filter_by_resource_lookup = 'resource'
#
#     def get_queryset(self, request):
#         ret = super().get_queryset(request)
#         ret = filter_for_resource(request, ret, lookup=self.filter_by_resource_lookup)
#         return ret


class ACLMixin:
    """Restrict access to superuser, owner, or manager."""
    def get_queryset(self, request):
        return self.model.objects.filter_acl(request.user)

    def get_object(self, request, *args, **kwargs):
        ret = super().get_object(request, *args, **kwargs)
        if not ret.is_accessible(request.user):
            raise self.model.DoesNotExist('Object does not exists or is unavailable')
        return ret


class ActiveQuerySet(models.QuerySet):
    def actives(self):
        return self.filter(active=True)


class ActiveManagerMixin:
    def active(self):
        return self.get_queryset().filter(active=True)
