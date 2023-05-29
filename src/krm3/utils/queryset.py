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


class OwnedMixin:
    """Restrict access to superuser, owner, or manager."""
    def get_queryset(self, request):
        return self.model.objects.owned(request.user)

    def get_object(self, request, object_id, from_field=None):
        ret = super().get_object(request, object_id, from_field)
        if not ret.is_owner(request.user):
            raise self.model.DoesNotExist('Object does not exists or is unavailable')
        return ret
