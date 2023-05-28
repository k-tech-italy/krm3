def filter_for_resource(request, queryset, lookup='resource'):
    if not request.user.is_superuser:
        queryset = queryset.filter(**{lookup: request.user.profile.resource})
    return queryset


class FilterByResourceMixin:
    filter_by_resource_lookup = 'resource'

    def get_queryset(self, request):
        ret = super().get_queryset(request)
        ret = filter_for_resource(request, ret, lookup=self.filter_by_resource_lookup)
        return ret
